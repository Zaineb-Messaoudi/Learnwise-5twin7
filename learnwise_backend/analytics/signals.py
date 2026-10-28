from django.apps import apps
from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import LearningActivity, Performance, QuestionConcept
from .services import evaluate_achievements, push_event, record_activity_effects

@receiver(post_save, sender=LearningActivity)
def activity_saved(sender, instance, created, **kwargs):
    if created:
        record_activity_effects(instance)

def refresh_assessment_performance(user, quiz):
    """Rebuild persisted performance from real evaluations and explicit mappings."""
    Question = apps.get_model("assessment", "Question")
    Evaluation = apps.get_model("assessment", "Evaluation")
    question_ids = Question.objects.filter(quiz=quiz).values_list("pk", flat=True)
    course_ids = QuestionConcept.objects.filter(question_id__in=question_ids).values_list(
        "concept__course_id", flat=True).distinct()
    for course_id in course_ids:
        mapped_question_ids = QuestionConcept.objects.filter(concept__course_id=course_id).values_list("question_id", flat=True)
        quiz_ids = Question.objects.filter(pk__in=mapped_question_ids).values_list("quiz_id", flat=True).distinct()
        aggregate = Evaluation.objects.filter(attempt__user=user, attempt__quiz_id__in=quiz_ids).aggregate(
            average=Avg("score"), count=Count("attempt_id", distinct=True))
        performance, _ = Performance.objects.get_or_create(user=user, course_id=course_id)
        performance.average_score = round(aggregate["average"] or 0, 2)
        performance.quiz_count = aggregate["count"] or 0
        performance.save(update_fields=("average_score", "quiz_count", "updated_at"))
        push_event(user.pk, "performance.updated", {"course_id": course_id,
                   "average_score": performance.average_score, "quiz_count": performance.quiz_count})
    evaluate_achievements(user)

def _evaluation_changed(sender, instance, **kwargs):
    refresh_assessment_performance(instance.attempt.user, instance.attempt.quiz)

Evaluation = apps.get_model("assessment", "Evaluation")
post_save.connect(_evaluation_changed, sender=Evaluation, dispatch_uid="analytics_evaluation_saved")
post_delete.connect(_evaluation_changed, sender=Evaluation, dispatch_uid="analytics_evaluation_deleted")

def _mapping_changed(sender, instance, **kwargs):
    Question = apps.get_model("assessment", "Question")
    question = Question.objects.filter(pk=instance.question_id).select_related("quiz").first()
    if not question:
        return
    user_ids = Evaluation.objects.filter(attempt__quiz=question.quiz).values_list("attempt__user_id", flat=True).distinct()
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(pk__in=user_ids):
        refresh_assessment_performance(user, question.quiz)

post_save.connect(_mapping_changed, sender=QuestionConcept, dispatch_uid="analytics_mapping_saved")
post_delete.connect(_mapping_changed, sender=QuestionConcept, dispatch_uid="analytics_mapping_deleted")
