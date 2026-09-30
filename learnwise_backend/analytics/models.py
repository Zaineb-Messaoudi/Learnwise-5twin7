from django.db import models
from django.conf import settings
from content.models import Course

class LearningPath(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_paths')
    title = models.CharField(max_length=255)

    def __str__(self):
        return f"Learning Path: {self.title} for {self.user.email}"

class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"Enrollment: {self.user.email} in {self.course.title}"

class LearningSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_sessions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='learning_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField(help_text="Duration in seconds")

    def __str__(self):
        return f"Session by {self.user.email} for {self.course.title}"

class LearningActivity(models.Model):
    session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50)
    started_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Activity {self.id} in session {self.session.id}"

class Progress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progress')
    completion_percentage = models.FloatField()

    def __str__(self):
        return f"Progress of {self.user.email} in {self.course.title}: {self.completion_percentage}%"

class Performance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='performance_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='performance')
    score = models.FloatField()

    def __str__(self):
        return f"Performance of {self.user.email} in {self.course.title}: {self.score}"

class Achievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=255)

    def __str__(self):
        return f"Achievement: {self.title} for {self.user.email}"
