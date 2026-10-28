"""Transcription vocale : Whisper (Hugging Face) d'abord, Gemini en secours.

Les fournisseurs essayes (et leur ordre) se reglent dans .env :
    TRANSCRIPTION_PROVIDERS=huggingface,gemini
"""
import logging
import os

from .config import get_setting
from .errors import AIServiceError
from .gemini_service import transcribe_audio_bytes
from .hf_common import hf_error

logger = logging.getLogger(__name__)


def _sanitize_for_log(value):
    """Supprime les caracteres de controle pour eviter l'injection dans les logs."""
    return ''.join(ch for ch in str(value) if ch >= ' ' and ch != '\x7f')


AUDIO_MIME_TYPES = {
    '.mp3': 'audio/mp3',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4',
    '.webm': 'audio/webm',
}


def _huggingface_transcribe(file_path):
    token = get_setting('HF_API_TOKEN')
    if not token:
        raise AIServiceError(
            'hf_not_configured', "Token HF_API_TOKEN manquant dans le fichier .env."
        )
    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        raise AIServiceError(
            'hf_sdk_missing', "Paquet manquant : pip install huggingface_hub"
        ) from exc

    try:
        client = InferenceClient(token=token)
        result = client.automatic_speech_recognition(
            file_path,
            model=get_setting('HF_WHISPER_MODEL', 'openai/whisper-large-v3'),
        )
    except Exception as exc:
        raise hf_error(
            exc,
            'transcription_error',
            "La transcription a echoue. Reessaie dans un instant.",
        ) from exc

    text = (getattr(result, 'text', '') or '').strip()
    if not text:
        raise AIServiceError(
            'transcription_empty', "Aucune parole detectee dans l'audio."
        )
    return text


def _gemini_transcribe(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    mime_type = AUDIO_MIME_TYPES.get(extension)
    if mime_type is None:
        raise AIServiceError(
            'audio_format_unsupported', "Format audio non pris en charge."
        )
    with open(file_path, 'rb') as audio_file:
        data = audio_file.read()
    return transcribe_audio_bytes(data, mime_type)


PROVIDERS = {'huggingface': _huggingface_transcribe, 'gemini': _gemini_transcribe}
PROVIDER_ALIASES = {
    'huggingface': 'huggingface',
    'gemini': 'gemini',
}


def transcribe_audio(file_path):
    names = get_setting('TRANSCRIPTION_PROVIDERS', 'huggingface,gemini').split(',')
    last_error = None
    for raw_name in names:
        normalized_name = raw_name.strip().lower()
        name = PROVIDER_ALIASES.get(normalized_name)
        if name is None:
            continue
        provider = PROVIDERS.get(name)
        if provider is None:
            continue
        try:
            return provider(file_path)
        except AIServiceError as exc:
            last_error = exc
            logger.warning(
                "Transcription : fournisseur %s indisponible (%s)",
                name,
                exc.code,
            )
    raise last_error or AIServiceError(
        'transcription_not_configured',
        "Aucun fournisseur de transcription configure (TRANSCRIPTION_PROVIDERS).",
    )