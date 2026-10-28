"""Gemini : reponses du chat, explications par niveau, prompts d'illustration.

Robustesse : si Gemini est surcharge (503, 429...), on reessaie quelques fois
avec une courte pause, puis on bascule sur un modele de secours.
"""
import logging
import time

from .config import get_setting
from .errors import AIServiceError

logger = logging.getLogger(__name__)


def _sanitize_for_log(value):
    """Nettoie une valeur avant journalisation pour eviter la log injection."""
    text = str(value)
    return text.replace('\r', '').replace('\n', '')


SYSTEM_PROMPT = (
    "Tu es l'assistant pedagogique de la plateforme Learnwise. "
    "Reponds dans la langue de l'etudiant, de facon claire, structuree et exacte. "
    "Si un contexte de cours est fourni, appuie-toi uniquement dessus pour les "
    "faits du cours et dis explicitement quand l'information n'y figure pas. "
    "N'invente jamais de references ni de citations."
)

LEVELS = {
    'beginner': "un debutant complet : vocabulaire simple, analogies, petits pas",
    'intermediate': "un etudiant de niveau intermediaire : precis, avec un exemple",
    'advanced': "un etudiant avance : rigoureux, avec nuances et cas limites",
}

# Codes d'erreur pour lesquels cela vaut la peine de reessayer.
RETRYABLE_CODES = {429, 500, 502, 503, 504}
ATTEMPTS_PER_MODEL = 3


def _candidate_models():
    """Modele principal puis modeles de secours (configurables dans .env)."""
    primary = get_setting('GEMINI_MODEL', 'gemini-flash-latest')
    fallbacks = get_setting('GEMINI_FALLBACK_MODELS', 'gemini-flash-lite-latest')
    ordered = []
    for name in [primary] + fallbacks.split(','):
        name = name.strip()
        if name and name not in ordered:
            ordered.append(name)
    return ordered


def _generate(turns, system_instruction=None, temperature=0.4):
    """turns : liste de tuples (role, texte) avec role = 'user' ou 'model'."""
    api_key = get_setting('GEMINI_API_KEY')
    if not api_key:
        raise AIServiceError(
            'gemini_not_configured',
            "Cle GEMINI_API_KEY manquante dans le fichier .env.",
        )
    try:
        from google import genai
        from google.genai import errors, types
    except ImportError as exc:
        raise AIServiceError(
            'gemini_sdk_missing', "Paquet manquant : pip install google-genai"
        ) from exc

    client = genai.Client(api_key=api_key)
    def _parts(content):
        items = content if isinstance(content, list) else [content]
        return [types.Part(text=i) if isinstance(i, str) else i for i in items]

    contents = [
        types.Content(role=role, parts=_parts(content))
        for role, content in turns
    ]
    config = types.GenerateContentConfig(
        system_instruction=system_instruction, temperature=temperature
    )

    codes_seen = []
    for model in _candidate_models():
        for attempt in range(1, ATTEMPTS_PER_MODEL + 1):
            try:
                response = client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except errors.APIError as exc:
                code = getattr(exc, 'code', None)
                codes_seen.append(code)
                logger.warning(
                    "Gemini modele=%s essai=%s/%s code=%s",
                    _sanitize_for_log(model), attempt, ATTEMPTS_PER_MODEL, code,
                )
                if code in RETRYABLE_CODES:
                    if attempt < ATTEMPTS_PER_MODEL:
                        time.sleep(2 ** (attempt - 1))  # pause : 1 s, puis 2 s
                        continue
                    break  # ce modele reste surcharge : on passe au suivant
                if code == 404:
                    break  # modele inexistant ou retire : on passe au suivant
                # 400 / 401 / 403 : reessayer ne servirait a rien
                raise AIServiceError(
                    'gemini_rejected',
                    "Gemini a refuse la requete (cle, format ou configuration invalide).",
                ) from exc
            except Exception as exc:
                logger.exception("Erreur inattendue avec Gemini")
                raise AIServiceError(
                    'gemini_error',
                    "Le service Gemini a echoue. Reessaie dans un instant.",
                    retryable=True,
                ) from exc

            text = (getattr(response, 'text', None) or '').strip()
            if text:
                logger.info("Gemini a repondu avec le modele %s", _sanitize_for_log(model))
                return text
            break  # reponse vide : on essaie le modele suivant

    if codes_seen and all(code == 404 for code in codes_seen):
        raise AIServiceError(
            'gemini_model_not_found',
            "Aucun modele Gemini disponible : verifie GEMINI_MODEL dans .env.",
        )
    raise AIServiceError(
        'gemini_unavailable',
        "Gemini est surcharge pour le moment. Reessaie dans quelques minutes.",
        retryable=True,
    )


def generate_answer(question, history=None, context=''):
    """history : liste de (role, texte) avec role 'user' ou 'assistant'."""
    turns = [
        ('user' if role == 'user' else 'model', text)
        for role, text in (history or [])
    ]
    prompt = question
    if context:
        prompt = (
            f"Contexte du cours :\n{context}\n\n"
            f"Question de l'etudiant :\n{question}"
        )
    turns.append(('user', prompt))
    return _generate(turns, SYSTEM_PROMPT)


def generate_explanation(answer, difficulty='intermediate'):
    audience = LEVELS.get(difficulty, LEVELS['intermediate'])
    prompt = (
        f"Explique en detail la reponse suivante pour {audience}.\n\n"
        f"Reponse a expliquer :\n{answer}"
    )
    return _generate([('user', prompt)], SYSTEM_PROMPT, temperature=0.5)


def build_image_prompt(answer):
    prompt = (
        "Ecris en anglais un prompt court (60 mots maximum) pour generer un "
        "diagramme pedagogique clair et sans aucun texte dans l'image, qui "
        f"illustre ceci :\n{answer[:1500]}\n\nReponds uniquement avec le prompt."
    )
    return _generate([('user', prompt)], temperature=0.7)


def transcribe_audio_bytes(data, mime_type):
    """Transcrit un audio avec Gemini (solution de secours a Whisper)."""
    try:
        from google.genai import types
    except ImportError as exc:
        raise AIServiceError(
            'gemini_sdk_missing', "Paquet manquant : pip install google-genai"
        ) from exc
    audio = types.Part.from_bytes(data=data, mime_type=mime_type)
    prompt = (
        "Transcris fidelement cet enregistrement audio, dans la langue parlee. "
        "Reponds uniquement avec la transcription, sans commentaire."
    )
    return _generate([('user', [audio, prompt])], temperature=0.0)