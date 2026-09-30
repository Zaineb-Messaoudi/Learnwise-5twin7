from django.db import models

class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    level = models.CharField(max_length=50)
    language = models.CharField(max_length=50)

    def __str__(self):
        return self.title

class CourseMaterial(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='course_materials/')
    material_type = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.title} ({self.course.title})"

class Transcription(models.Model):
    material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='transcriptions')
    content = models.TextField()
    language = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcription for {self.material.title}"

class Summary(models.Model):
    material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='summaries')
    content = models.TextField()
    summary_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary for {self.material.title}"

class AudioMaterial(models.Model):
    material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='audio_details')
    audio_file = models.FileField(upload_to='audio_materials/')
    duration = models.IntegerField(help_text="Duration in seconds")
    language = models.CharField(max_length=50)

    def __str__(self):
        return f"Audio for {self.material.title}"

class DocumentMaterial(models.Model):
    material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='document_details')
    pdf_file = models.FileField(upload_to='document_materials/')
    page_count = models.IntegerField()

    def __str__(self):
        return f"Document for {self.material.title}"
