from django.db import models
from django.conf import settings


class Notebook(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notebooks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course = models.ForeignKey('content.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='notebooks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notebooks_notebook'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title


class NotebookEntry(models.Model):
    ENTRY_TYPES = [
        ('note', 'Note'),
        ('summary', 'Summary'),
        ('flashcard', 'Flashcard'),
        ('quiz', 'Quiz'),
        ('mindmap', 'Mind Map'),
    ]

    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, related_name='entries')
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES, default='note')
    title = models.CharField(max_length=255)
    content = models.JSONField(default=dict)
    source_material_id = models.CharField(max_length=100, blank=True, default='')
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notebooks_entry'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.notebook.title} - {self.title}"