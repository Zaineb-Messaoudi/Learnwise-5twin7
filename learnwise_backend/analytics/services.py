from datetime import timedelta
from django.db import transaction
from django.db.models import Avg, Sum
from django.utils import timezone
from .models import Achievement, LearningActivity, LearningSession, Performance, Progress

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

def evaluate_achievements(user):
    earned = []
    if LearningActivity.objects.filter(session__user=user, activity_type=LearningActivity.Type.QUIZ).exists():
        earned.append(award(user, Achievement.Code.FIRST_QUIZ)[0])
    if LearningSession.objects.filter(user=user, ended_at__isnull=False).count() >= 5:
        earned.append(award(user, Achievement.Code.FIVE_SESSIONS)[0])
    if Progress.objects.filter(user=user, completion_percentage__gte=100).exists():
        earned.append(award(user, Achievement.Code.COURSE_COMPLETE)[0])
    if Performance.objects.filter(user=user, average_score__gte=80, quiz_count__gt=0).exists():
        earned.append(award(user, Achievement.Code.HIGH_SCORE)[0])
    return earned

def record_activity_effects(activity):
    progress, _ = Progress.objects.get_or_create(user=activity.session.user, course=activity.session.course)
    if activity.activity_type == LearningActivity.Type.LESSON_COMPLETED:
        total = max(activity.session.course.materials.count(), 1)
        completed = LearningActivity.objects.filter(
            session__user=activity.session.user,
            session__course=activity.session.course,
            activity_type=LearningActivity.Type.LESSON_COMPLETED,
        ).values("reference_id").distinct().count()
        progress.completion_percentage = min(100, completed * 100 / total)
    progress.last_activity = activity.completed_at or activity.started_at
    progress.save(update_fields=("completion_percentage", "last_activity"))
    evaluate_achievements(activity.session.user)
    transaction.on_commit(lambda: push_event(activity.session.user_id, "progress.updated", {
        "course_id": activity.session.course_id,
        "completion_percentage": progress.completion_percentage,
        "last_activity": progress.last_activity.isoformat(),
    }))

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
    return {
        "data_source": "live",
        "stats": {
            "learning_hours": round((sessions.aggregate(v=Sum("duration"))["v"] or 0) / 3600, 1),
            "average_quiz_score": round(performances.aggregate(v=Avg("average_score"))["v"] or 0, 1),
            "streak_days": _streak(user),
            "achievement_count": Achievement.objects.filter(user=user).count(),
            "courses_enrolled": user.enrollments.filter(status="active").count(),
        },
        "weekly_activity": [{"label": key, "hours": round(value, 2)} for key, value in sorted(daily.items())],
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
    day, count = timezone.localdate(), 0
    while day in dates:
        count += 1
        day -= timedelta(days=1)
    return count
