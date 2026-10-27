from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LearningActivity, Performance
from .services import evaluate_achievements, record_activity_effects

@receiver(post_save, sender=LearningActivity)
def activity_saved(sender, instance, created, **kwargs):
    if created:
        record_activity_effects(instance)

def _evaluation_saved(sender, instance, created, **kwargs):
    """Assessment adapter: inactive until Quiz exposes a course relation."""
    if not created:
        return
    attempt = instance.attempt
    course = getattr(attempt.quiz, "course", None)
    if course is None:
        return
    values = sender.objects.filter(attempt__user=attempt.user, attempt__quiz__course=course).values_list("score", flat=True)
    scores = list(values)
    performance, _ = Performance.objects.get_or_create(user=attempt.user, course=course)
    performance.average_score = sum(scores) / len(scores)
    performance.quiz_count = len(scores)
    performance.save(update_fields=("average_score", "quiz_count", "updated_at"))
    evaluate_achievements(attempt.user)

Evaluation = apps.get_model("assessment", "Evaluation")
post_save.connect(_evaluation_saved, sender=Evaluation, dispatch_uid="analytics_evaluation_adapter")
