from django.db import models
from django.conf import settings

class Quiz(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    difficulty = models.CharField(max_length=50)

    def __str__(self):
        return self.title

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    type = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=50)

    def __str__(self):
        return f"Question {self.id} in {self.quiz.title}"

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)

    def __str__(self):
        return f"Choice for {self.question.id}: {self.text}"

class QuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attempt by {self.user.email} for {self.quiz.title}"

class Answer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField()

    def __str__(self):
        return f"Answer for {self.question.id} in attempt {self.attempt.id}"

class Evaluation(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='evaluations')
    score = models.FloatField()
    feedback = models.TextField()

    def __str__(self):
        return f"Evaluation for attempt {self.attempt.id}"

class Exercise(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='exercises')
    content = models.TextField()

    def __str__(self):
        return f"Exercise in {self.quiz.title}"
