# Squashed migration for analytics app
# Combines 0001_initial (BigAutoField ids) and 0002_alter_* (UUIDField ids)
# into a single migration that creates all models with UUID ids directly,
# avoiding MySQL's inability to ALTER COLUMN BIGINT -> UUID.

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('content', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LearningPath',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learning_paths', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed'), ('dropped', 'Dropped')], default='active', max_length=20)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to='content.course')),
                ('learning_path', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='enrollments', to='analytics.learningpath')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-enrolled_at',),
                'constraints': [
                    models.UniqueConstraint(fields=('user', 'course'), name='analytics_unique_enrollment'),
                ],
                'indexes': [
                    models.Index(fields=('user', 'course'), name='analytics_enroll_user_course'),
                ],
            },
        ),
        migrations.CreateModel(
            name='LearningSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('duration', models.PositiveIntegerField(default=0, help_text='Duration in seconds')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learning_sessions', to='content.course')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learning_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-started_at',),
                'indexes': [
                    models.Index(fields=('user', 'course'), name='analytics_session_user_course'),
                ],
            },
        ),
        migrations.CreateModel(
            name='LearningActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('activity_type', models.CharField(choices=[('course_view', 'Course view'), ('lesson_started', 'Lesson started'), ('lesson_completed', 'Lesson completed'), ('quiz', 'Quiz'), ('exercise', 'Exercise'), ('voice_question', 'Voice question')], max_length=40)),
                ('reference_id', models.UUIDField(blank=True, null=True)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='analytics.learningsession')),
            ],
            options={
                'ordering': ('-started_at',),
                'indexes': [
                    models.Index(fields=('session', 'activity_type'), name='an_activity_session_type'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Performance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('average_score', models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('exercise_count', models.PositiveIntegerField(default=0)),
                ('quiz_count', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='performance', to='content.course')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='performance_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-updated_at',),
                'constraints': [
                    models.UniqueConstraint(fields=('user', 'course'), name='analytics_unique_performance'),
                ],
                'indexes': [
                    models.Index(fields=('user', 'course'), name='analytics_perf_user_course'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Progress',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('completion_percentage', models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('last_activity', models.DateTimeField(default=django.utils.timezone.now)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='content.course')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-last_activity',),
                'constraints': [
                    models.UniqueConstraint(fields=('user', 'course'), name='analytics_unique_progress'),
                ],
                'indexes': [
                    models.Index(fields=('user', 'course'), name='analytics_progress_user_course'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Achievement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(choices=[('legacy', 'Legacy achievement'), ('first_quiz', 'First quiz'), ('five_sessions', 'Five sessions'), ('course_complete', 'Course complete'), ('high_score', 'High score')], default='legacy', max_length=40)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('earned_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='achievements', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-earned_at',),
                'constraints': [
                    models.UniqueConstraint(fields=('user', 'code'), name='analytics_unique_achievement'),
                ],
                'indexes': [
                    models.Index(fields=('user', 'earned_at'), name='an_achievement_user_date'),
                ],
            },
        ),
    ]
