"""Learning Radar: explainable early-warning signals, never generated prose."""
from datetime import datetime, time, timedelta
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from .models import (Intervention, LearningRisk, LearningSession, Performance, Progress,
                     WeeklyLearningSnapshot)
from .reporting import concept_weaknesses
from .services import push_event


def _week_start(day=None):
    day = day or timezone.localdate()
    return day - timedelta(days=day.weekday())


def build_current_snapshot(user, course):
    start = _week_start()
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    sessions = LearningSession.objects.filter(user=user, course=course, started_at__gte=start_dt)
    aggregates = sessions.aggregate(seconds=Sum("duration"), sessions=Count("id"))
    completed = sessions.filter(ended_at__isnull=False).count()
    performance = Performance.objects.filter(user=user, course=course).first()
    progress = Progress.objects.filter(user=user, course=course).first()
    weakness = concept_weaknesses(user, minimum_answers=1)
    course_weaknesses = [item for item in weakness.get("concepts", []) if item["course_id"] == course.pk]
    error_rate = max((item["error_rate"] for item in course_weaknesses), default=None)
    snapshot, _ = WeeklyLearningSnapshot.objects.update_or_create(
        user=user, course=course, week_start=start,
        defaults={
            "learning_seconds": aggregates["seconds"] or 0,
            "session_count": aggregates["sessions"] or 0,
            "completed_session_count": completed,
            "average_score": performance.average_score if performance and performance.quiz_count else None,
            "assessment_count": (performance.quiz_count + performance.exercise_count) if performance else 0,
            "completion_percentage": progress.completion_percentage if progress else 0,
            "concept_error_rate": error_rate,
            "evidence": {"session_ids": [str(pk) for pk in sessions.values_list("pk", flat=True)],
                         "performance_id": str(performance.pk) if performance else None,
                         "progress_id": str(progress.pk) if progress else None},
        },
    )
    return snapshot


def _anomaly_signal(snapshots):
    if len(snapshots) < 8:
        return None
    import numpy as np
    from sklearn.ensemble import IsolationForest
    matrix = np.array([[s.learning_seconds, s.session_count, s.average_score or 0,
                        s.completion_percentage, s.concept_error_rate or 0] for s in snapshots], dtype=float)
    prediction = IsolationForest(contamination="auto", random_state=42).fit_predict(matrix)
    if prediction[-1] != -1:
        return None
    return {"signal": "behavior_anomaly", "value": "detected", "threshold": "IsolationForest outlier",
            "observations": len(snapshots), "weight": 0.2}


def evaluate_course_risk(user, course, *, notify=True):
    current = build_current_snapshot(user, course)
    snapshots = list(WeeklyLearningSnapshot.objects.filter(user=user, course=course).order_by("week_start"))
    progress = Progress.objects.filter(user=user, course=course).first()
    signals = []
    if progress:
        inactive_days = max(0, (timezone.localdate() - timezone.localtime(progress.last_activity).date()).days)
        if inactive_days >= 5 and progress.completion_percentage < 100:
            signals.append({"signal": "inactive_days", "value": inactive_days, "threshold": 5,
                            "observations": 1, "weight": 0.3 if inactive_days < 10 else 0.45})
    if len(snapshots) >= 2:
        previous = snapshots[-2]
        delta = current.completion_percentage - previous.completion_percentage
        if delta <= 1 and current.completion_percentage < 100:
            signals.append({"signal": "stalled_progress", "value": round(delta, 2), "threshold": 1,
                            "observations": 2, "weight": 0.25})
        if previous.learning_seconds and current.learning_seconds < previous.learning_seconds * 0.7:
            drop = round((1 - current.learning_seconds / previous.learning_seconds) * 100, 2)
            signals.append({"signal": "learning_time_drop", "value": drop, "threshold": 30,
                            "observations": 2, "weight": 0.25})
    if current.assessment_count >= 3 and current.average_score is not None and current.average_score < 50:
        signals.append({"signal": "low_average_score", "value": round(current.average_score, 2), "threshold": 50,
                        "observations": current.assessment_count, "weight": 0.4})
    if current.concept_error_rate is not None and current.concept_error_rate >= 60:
        signals.append({"signal": "high_concept_error_rate", "value": current.concept_error_rate, "threshold": 60,
                        "observations": current.assessment_count, "weight": 0.35})
    anomaly = _anomaly_signal(snapshots)
    if anomaly:
        signals.append(anomaly)
    score = min(1, sum(signal["weight"] for signal in signals))
    existing = LearningRisk.objects.filter(user=user, course=course, status=LearningRisk.Status.OPEN).first()
    if not signals:
        if existing:
            existing.status, existing.resolved_at = LearningRisk.Status.RESOLVED, timezone.now()
            existing.save(update_fields=("status", "resolved_at"))
        return None
    level = LearningRisk.Level.HIGH if score >= 0.65 else LearningRisk.Level.MEDIUM if score >= 0.35 else LearningRisk.Level.LOW
    observations = max((signal["observations"] for signal in signals), default=0)
    confidence = LearningRisk.Level.HIGH if observations >= 10 else LearningRisk.Level.MEDIUM if observations >= 3 else LearningRisk.Level.LOW
    risk = existing or LearningRisk(user=user, course=course)
    risk.risk_level, risk.risk_score, risk.confidence = level, round(score, 2), confidence
    risk.evidence = signals
    risk.model_version = "rules-v1+isolation-forest-v1" if anomaly else "rules-v1"
    risk.detected_at = timezone.now()
    risk.save()
    _build_interventions(risk)
    if notify:
        transaction.on_commit(lambda: push_event(user.pk, "learning_risk.updated", {
            "risk_id": str(risk.pk), "course_id": course.pk, "level": level, "score": risk.risk_score}))
    return risk


def _build_interventions(risk):
    risk.interventions.filter(completed_at__isnull=True).delete()
    actions = []
    signals = {item["signal"] for item in risk.evidence}
    if signals & {"inactive_days", "stalled_progress", "learning_time_drop"}:
        actions.append((Intervention.Action.RESUME_COURSE, f"Reprendre {risk.course.title}",
                        "L'activité ou la progression a diminué.", 1, 20))
    if "high_concept_error_rate" in signals:
        actions.append((Intervention.Action.REVIEW_CONCEPT, "Réviser la notion la plus fragile",
                        "Le taux d'erreur mappé dépasse 60 %.", 1, 15))
    if "low_average_score" in signals:
        actions.append((Intervention.Action.TAKE_QUIZ, "Faire un quiz ciblé",
                        "Le score moyen est inférieur à 50 %.", 2, 10))
    if not actions:
        actions.append((Intervention.Action.SHORT_SESSION, "Planifier une session courte",
                        "Une anomalie de rythme a été détectée.", 1, 15))
    Intervention.objects.bulk_create([Intervention(risk=risk, action_type=a, title=t, reason=r,
                                                    priority=p, estimated_minutes=m)
                                      for a, t, r, p, m in actions])


def radar_for(user):
    risks = LearningRisk.objects.filter(user=user, status=LearningRisk.Status.OPEN).select_related("course").prefetch_related("interventions")
    return {"status": "available", "generated_at": timezone.now(), "risks": [{
        "id": str(risk.pk), "course_id": risk.course_id, "course": risk.course.title,
        "risk_level": risk.risk_level, "risk_score": risk.risk_score, "confidence": risk.confidence,
        "evidence": risk.evidence, "model_version": risk.model_version, "detected_at": risk.detected_at,
        "interventions": [{"id": str(item.pk), "type": item.action_type, "title": item.title,
                           "reason": item.reason, "priority": item.priority,
                           "estimated_minutes": item.estimated_minutes, "completed_at": item.completed_at}
                          for item in risk.interventions.all()]}
        for risk in risks]}
