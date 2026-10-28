"""Best-effort adapters from content/assessment into analytics."""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LearningActivity
from .services import ensure_enrollment, evaluate_achievements, push_event, recompute_performance, recompute_progress, record_activity_effects


@receiver(post_save, sender=LearningActivity)
def activity_saved(sender, instance, created, **kwargs):
    if created:
        record_activity_effects(instance)


def _evaluation_saved(sender, instance, created, **kwargs):
    if not created:
        return
    course = getattr(instance.attempt.quiz, "course", None)
    if not course:
        return
    user = instance.attempt.user
    ensure_enrollment(user, course)
    performance = recompute_performance(user, course)
    evaluate_achievements(user)
    transaction.on_commit(lambda: push_event(user.pk, "performance.updated", {"course_id": course.pk, "average_score": performance.average_score}))


def _exercise_saved(sender, instance, created, **kwargs):
    if not created or not instance.exercise.course_id:
        return
    performance = recompute_performance(instance.user, instance.exercise.course)
    transaction.on_commit(lambda: push_event(instance.user_id, "performance.updated", {"course_id": instance.exercise.course_id, "exercise_count": performance.exercise_count}))


def _lesson_completion_saved(sender, instance, created, **kwargs):
    if not created:
        return
    course = instance.material.course
    ensure_enrollment(instance.user, course)
    progress = recompute_progress(instance.user, course)
    evaluate_achievements(instance.user)
    transaction.on_commit(lambda: push_event(instance.user_id, "progress.updated", {"course_id": course.pk, "completion_percentage": progress.completion_percentage}))


def _badge_saved(sender, instance, created, **kwargs):
    if created:
        evaluate_achievements(instance.user)
        transaction.on_commit(lambda: push_event(instance.user_id, "achievement.earned", {"course_id": instance.course_id, "name": instance.name}))


post_save.connect(_evaluation_saved, sender="assessment.Evaluation", dispatch_uid="analytics_evaluation_adapter")
post_save.connect(_exercise_saved, sender="assessment.ExerciseSubmission", dispatch_uid="analytics_exercise_adapter")
post_save.connect(_lesson_completion_saved, sender="content.LessonCompletion", dispatch_uid="analytics_lesson_completion_adapter")
post_save.connect(_badge_saved, sender="content.Badge", dispatch_uid="analytics_badge_adapter")
