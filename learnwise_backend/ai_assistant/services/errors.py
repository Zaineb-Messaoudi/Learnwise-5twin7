class AIServiceError(Exception):
    """Erreur controlee d'un service IA (Gemini, Whisper, Hugging Face)."""

    def __init__(self, code, message, retryable=False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
