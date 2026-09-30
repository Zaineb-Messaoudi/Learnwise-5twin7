from django.db import models
from django.conf import settings

class AssistantSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assistant_sessions')
    started_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} - User {self.user.email}"

class VoiceQuestion(models.Model):
    session = models.ForeignKey(AssistantSession, on_delete=models.CASCADE, related_name='voice_questions')
    audio_file = models.FileField(upload_to='voice_questions/')

    def __str__(self):
        return f"Voice Question for session {self.session.id}"

class AssistantMessage(models.Model):
    session = models.ForeignKey(AssistantSession, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in session {self.session.id}"

class Explanation(models.Model):
    message = models.ForeignKey(AssistantMessage, on_delete=models.CASCADE, related_name='explanations')
    content = models.TextField()

    def __str__(self):
        return f"Explanation for message {self.message.id}"

class Illustration(models.Model):
    message = models.ForeignKey(AssistantMessage, on_delete=models.CASCADE, related_name='illustrations')
    image = models.ImageField(upload_to='assistant_illustrations/')

    def __str__(self):
        return f"Illustration for message {self.message.id}"
