"""Outils communs aux services Hugging Face (voix et images)."""
import re


from .errors import AIServiceError


def hf_status_code(exc):
    """Retourne le code HTTP d'une erreur Hugging Face (402, 403...) ou None."""
    response = getattr(exc, 'response', None)
    code = getattr(response, 'status_code', None)
    if isinstance(code, int):
        return code
    match = re.search(r'\b(401|402|403|404|429)\b', str(exc))
    return int(match.group(1)) if match else None


def hf_error(exc, default_code, default_message):
    """Transforme une erreur Hugging Face en AIServiceError claire."""
    status = hf_status_code(exc)
    if status == 402:
        return AIServiceError(
            'hf_quota_exceeded',
            "Les credits gratuits Hugging Face de ce mois sont epuises.",
        )
    if status in (401, 403):
        return AIServiceError(
            'hf_permission_denied',
            "Le token Hugging Face n'a pas la permission d'appeler "
            "les Inference Providers.",
        )
    if status == 429:
        return AIServiceError(
            default_code,
            "Trop de demandes envoyees a Hugging Face. Reessaie dans un instant.",
            retryable=True,
        )
    return AIServiceError(default_code, default_message, retryable=True)