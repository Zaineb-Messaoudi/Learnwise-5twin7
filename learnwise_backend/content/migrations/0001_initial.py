import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('level', models.CharField(max_length=50, blank=True)),
                ('language', models.CharField(max_length=50, default='fr')),
            ],
            options={
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='CourseMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('file', models.FileField(upload_to='course_materials/')),
                ('material_type', models.CharField(default='other', max_length=20)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='content.course')),
            ],
        ),
        migrations.CreateModel(
            name='AudioMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duration', models.IntegerField(blank=True, help_text='Durée en secondes', null=True)),
                ('language', models.CharField(blank=True, max_length=50)),
                ('material', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='audio_details', to='content.coursematerial')),
            ],
        ),
        migrations.CreateModel(
            name='DocumentMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_count', models.IntegerField(blank=True, null=True)),
                ('mime_type', models.CharField(blank=True, max_length=100)),
                ('material', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='document_details', to='content.coursematerial')),
            ],
        ),
        migrations.CreateModel(
            name='Transcription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(blank=True)),
                ('language', models.CharField(blank=True, max_length=50)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transcriptions', to='content.coursematerial')),
            ],
        ),
        migrations.CreateModel(
            name='Summary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(blank=True)),
                ('summary_type', models.CharField(default='general', max_length=50)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='summaries', to='content.coursematerial')),
            ],
        ),
    ]
