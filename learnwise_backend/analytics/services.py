from datetime import timedelta
from django.db import transaction
from django.db.models import Avg, Sum, Count, OuterRef, Subquery
from django.utils import timezone
from .models import Achievement, Enrollment, LearningActivity, LearningSession, Performance, Progress

BADGES = {
    Achievement.Code.FIRST_QUIZ: ("Premier quiz", "Vous avez terminé votre premier quiz."),
    Achievement.Code.FIVE_SESSIONS: ("Rythme lancé", "Vous avez réalisé cinq sessions d'apprentissage."),
    Achievement.Code.COURSE_COMPLETE: ("Cours terminé", "Vous avez terminé un cours à 100 %."),
    Achievement.Code.HIGH_SCORE: ("Excellent score", "Vous avez obtenu un score supérieur ou égal à 80 %."),
}

def push_event(user_id, event_type, payload):
    """Best-effort notification; analytics writes must not depend on Redis."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        async_to_sync(get_channel_layer().group_send)(
            f"analytics_{user_id}", {"type": "analytics.event", "event": event_type, "payload": payload}
        )
    except Exception:
        return

def award(user, code):
    title, description = BADGES[code]
    achievement, created = Achievement.objects.get_or_create(
        user=user, code=code, defaults={"title": title, "description": description}
    )
    if created:
        transaction.on_commit(lambda: push_event(user.pk, "achievement.earned", {"id": str(achievement.pk), "title": title}))
    return achievement, created

def ensure_enrollment(user, course):
    if not user or not user.is_authenticated or user.role != "etudiant" or not course or course.status != "published":
        return None
    enrollment, _ = Enrollment.objects.get_or_create(user=user, course=course)
    Progress.objects.get_or_create(user=user, course=course)
    Performance.objects.get_or_create(user=user, course=course)
    return enrollment

def recompute_progress(user, course):
    if not user or not course:
        return None
    total = course.materials.count()
    completed = course.materials.filter(completions__user=user).distinct().count()
    percentage = 100 if total == 0 else min(100, completed * 100 / total)
    progress, _ = Progress.objects.update_or_create(
        user=user, course=course,
        defaults={"completion_percentage": percentage, "last_activity": timezone.now()},
    )
    enrollment = Enrollment.objects.filter(user=user, course=course).first()
    if enrollment and percentage >= 100 and enrollment.status == Enrollment.Status.ACTIVE:
        enrollment.status = Enrollment.Status.COMPLETED
        enrollment.save(update_fields=("status",))
    return progress

def recompute_performance(user, course):
    from assessment.models import Evaluation, ExerciseSubmission
    latest = Evaluation.objects.filter(
        attempt__user=user, attempt__quiz__course=course,
        attempt__quiz_id=OuterRef("attempt__quiz_id"),
    ).order_by("-created_at", "-pk")
    evaluations = Evaluation.objects.filter(
        attempt__user=user, attempt__quiz__course=course,
    ).filter(pk=Subquery(latest.values("pk")[:1]))
    scores = list(evaluations.values_list("correct_answers", "total_questions"))
    percentages = [correct * 100 / total for correct, total in scores if total]
    exercises = ExerciseSubmission.objects.filter(user=user, exercise__course=course).values("exercise_id").distinct().count()
    performance, _ = Performance.objects.update_or_create(
        user=user, course=course,
        defaults={"average_score": sum(percentages) / len(percentages) if percentages else 0,
                  "quiz_count": len(scores), "exercise_count": exercises},
    )
    return performance

def evaluate_achievements(user):
    earned = []
    if LearningActivity.objects.filter(session__user=user, activity_type=LearningActivity.Type.QUIZ).exists():
        earned.append(award(user, Achievement.Code.FIRST_QUIZ)[0])
    if LearningSession.objects.filter(user=user, ended_at__isnull=False).count() >= 5:
        earned.append(award(user, Achievement.Code.FIVE_SESSIONS)[0])
    if Progress.objects.filter(user=user, completion_percentage__gte=100).exists() or user.badges_earned.exists():
        earned.append(award(user, Achievement.Code.COURSE_COMPLETE)[0])
    if Performance.objects.filter(user=user, average_score__gte=80, quiz_count__gt=0).exists():
        earned.append(award(user, Achievement.Code.HIGH_SCORE)[0])
    return earned

def record_activity_effects(activity):
    progress, _ = Progress.objects.get_or_create(user=activity.session.user, course=activity.session.course)
    progress.last_activity = activity.completed_at or activity.started_at
    progress.save(update_fields=("last_activity",))

def recommendations_for(user):
    now = timezone.now()
    items = []
    for perf in Performance.objects.filter(user=user, average_score__lt=60).select_related("course")[:3]:
        items.append({"type": "weak_score", "priority": "high", "course_id": perf.course_id,
                      "title": f"Retravailler {perf.course.title}", "reason": f"Score moyen de {perf.average_score:.0f} %."})
    for progress in Progress.objects.filter(user=user, completion_percentage__gt=0, completion_percentage__lt=100,
                                             last_activity__lt=now - timedelta(days=7)).select_related("course")[:3]:
        items.append({"type": "inactive_course", "priority": "medium", "course_id": progress.course_id,
                      "title": f"Reprendre {progress.course.title}", "reason": "Aucune activité depuis plus de 7 jours."})
    for progress in Progress.objects.filter(user=user, completion_percentage__gte=60, completion_percentage__lt=100).select_related("course")[:3]:
        items.append({"type": "next_quiz", "priority": "low", "course_id": progress.course_id,
                      "title": f"Tester vos acquis : {progress.course.title}", "reason": "Votre progression est idéale pour un quiz."})
    return items[:6]

def dashboard_for(user, days=30):
    since = timezone.now() - timedelta(days=days)
    sessions = LearningSession.objects.filter(user=user, started_at__gte=since)
    performances = Performance.objects.filter(user=user)
    measured_performances = list(performances.filter(quiz_count__gt=0))
    assessment_count = sum(item.quiz_count for item in measured_performances)
    weighted_score = (sum(item.average_score * item.quiz_count for item in measured_performances) /
                      assessment_count if assessment_count else 0)
    daily = {}
    for session in sessions:
        key = session.started_at.date().isoformat()
        daily[key] = daily.get(key, 0) + session.duration / 3600
    recommendations = recommendations_for(user)
    next_move = None
    if recommendations:
        recommendation = recommendations[0]
        next_move = {
            "course_title": recommendation["title"],
            "current_topic": recommendation["reason"],
            "next_topic": recommendation["title"],
            "action": "Activité recommandée",
            "estimated_minutes": 15,
            "difficulty": recommendation["priority"],
            "href": f"/student/courses/{recommendation['course_id']}",
        }
    today = timezone.localdate()
    weekly = [
        {"label": (today - timedelta(days=offset)).isoformat(),
         "hours": round(daily.get((today - timedelta(days=offset)).isoformat(), 0), 2)}
        for offset in range(6, -1, -1)
    ]
    return {
        "data_source": "live",
        "stats": {
            "learning_hours": round((sessions.aggregate(v=Sum("duration"))["v"] or 0) / 3600, 1),
            "average_quiz_score": round(weighted_score, 1),
            "assessment_count": assessment_count,
            "streak_days": _streak(user),
            "achievement_count": Achievement.objects.filter(user=user).count(),
            "courses_enrolled": user.enrollments.filter(status="active").count(),
        },
        "weekly_activity": weekly,
        "focus_areas": [{"name": p.course.title, "score": round(p.average_score), "trend": "À retravailler"}
                        for p in performances.filter(average_score__lt=70).select_related("course")[:5]],
        "progress": [{"course_id": p.course_id, "course": p.course.title, "percentage": p.completion_percentage}
                     for p in Progress.objects.filter(user=user).select_related("course")],
        "achievements": list(Achievement.objects.filter(user=user).values("id", "title", "description", "earned_at")[:5]),
        "recommendations": recommendations,
        "next_best_move": next_move,
        "recent_sessions": [{"id": str(item.pk), "course": item.course.title,
                             "started_at": item.started_at, "duration": item.duration}
                            for item in sessions.select_related("course")[:10]],
    }

def _streak(user):
    dates = set(LearningSession.objects.filter(user=user, ended_at__isnull=False).values_list("started_at__date", flat=True))
    day = timezone.localdate()
    if day not in dates:
        day -= timedelta(days=1)
    count = 0
    while day in dates:
        count += 1
        day -= timedelta(days=1)
    return count
