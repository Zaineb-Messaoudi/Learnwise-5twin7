"""Evidence-based reports: every number includes its source and sample size."""
from django.apps import apps
from django.db.models import Avg, Count, Sum
from .models import Cohort, LearningSession, Performance, Progress, QuestionConcept


def _metric(value, observations, formula, sources, status="available"):
    return {
        "status": status,
        "value": value if status == "available" else None,
        "observations": observations,
        "formula": formula,
        "sources": sources,
    }


def student_course_indicators(user):
    """Explain persisted student indicators; do not synthesize missing scores."""
    rows = []
    course_ids = set(Progress.objects.filter(user=user).values_list("course_id", flat=True))
    course_ids.update(Performance.objects.filter(user=user).values_list("course_id", flat=True))
    course_ids.update(LearningSession.objects.filter(user=user).values_list("course_id", flat=True))
    Course = apps.get_model("content", "Course")
    courses = {course.pk: course for course in Course.objects.filter(pk__in=course_ids)}
    for course_id in sorted(course_ids):
        progress = Progress.objects.filter(user=user, course_id=course_id).first()
        performance = Performance.objects.filter(user=user, course_id=course_id).first()
        sessions = LearningSession.objects.filter(user=user, course_id=course_id, ended_at__isnull=False)
        session_data = sessions.aggregate(seconds=Sum("duration"), count=Count("id"))
        assessment_count = (performance.quiz_count + performance.exercise_count) if performance else 0
        rows.append({
            "course_id": course_id,
            "course": courses[course_id].title,
            "completion": _metric(
                round(progress.completion_percentage, 2), 1,
                "Valeur persistée de Progress.completion_percentage.",
                ["analytics.Progress"],
            ) if progress else _metric(None, 0, "Aucun Progress disponible.", ["analytics.Progress"], "insufficient_data"),
            "average_score": _metric(
                round(performance.average_score, 2), assessment_count,
                "Moyenne déjà calculée et persistée dans Performance.average_score.",
                ["analytics.Performance", "assessment.Evaluation"],
            ) if performance and assessment_count else _metric(
                None, 0, "Aucune évaluation comptabilisée.",
                ["analytics.Performance", "assessment.Evaluation"], "insufficient_data"),
            "time_spent_seconds": _metric(
                int(session_data["seconds"] or 0), int(session_data["count"] or 0),
                "Somme des durées des sessions terminées.", ["analytics.LearningSession"],
            ) if session_data["count"] else _metric(
                None, 0, "Aucune session terminée.", ["analytics.LearningSession"], "insufficient_data"),
        })
    return {"status": "available" if rows else "insufficient_data", "courses": rows}


def concept_weaknesses(user, minimum_answers=2):
    """Aggregate real wrong answers through explicit question→concept mappings."""
    import pandas as pd
    Answer = apps.get_model("assessment", "Answer")
    mappings = list(QuestionConcept.objects.select_related("concept", "concept__course").values(
        "question_id", "concept_id", "concept__title", "concept__course_id", "concept__course__title", "weight"
    ))
    if not mappings:
        return {"status": "insufficient_data", "reason": "Aucune question n'est reliée à une notion.",
                "sources": ["analytics.QuestionConcept", "assessment.Answer"], "concepts": []}
    mapping_by_question = {}
    for mapping in mappings:
        mapping_by_question.setdefault(mapping["question_id"], []).append(mapping)
    answers = Answer.objects.filter(attempt__user=user, question_id__in=mapping_by_question).values("question_id", "is_correct")
    evidence = []
    for answer in answers:
        for mapping in mapping_by_question[answer["question_id"]]:
            evidence.append({**mapping, "error_weight": 0 if answer["is_correct"] else mapping["weight"],
                             "answer_weight": mapping["weight"]})
    if not evidence:
        return {"status": "insufficient_data", "reason": "Aucune réponse mappée n'est disponible pour cet étudiant.",
                "sources": ["analytics.QuestionConcept", "assessment.Answer"], "concepts": []}
    frame = pd.DataFrame(evidence)
    grouped = frame.groupby(["concept_id", "concept__title", "concept__course_id", "concept__course__title"], as_index=False).agg(
        answers=("question_id", "count"), error_weight=("error_weight", "sum"), answer_weight=("answer_weight", "sum")
    )
    grouped["error_rate"] = grouped["error_weight"] / grouped["answer_weight"] * 100
    grouped = grouped[grouped["answers"] >= minimum_answers].sort_values(["error_rate", "answers"], ascending=False)
    concepts = [{"concept_id": str(row.concept_id), "concept": row["concept__title"],
                 "course_id": int(row["concept__course_id"]), "course": row["concept__course__title"],
                 "answers": int(row.answers), "error_rate": round(float(row.error_rate), 2),
                 "formula": "Somme pondérée des erreurs / somme des poids des réponses × 100."}
                for _, row in grouped.iterrows()]
    return {"status": "available" if concepts else "insufficient_data",
            "reason": None if concepts else f"Moins de {minimum_answers} réponses par notion.",
            "sources": ["analytics.QuestionConcept", "assessment.Answer"], "concepts": concepts}


def cohort_comparison(cohort: Cohort):
    """Aggregate a declared cohort by course/subject and actual quiz evaluations."""
    import pandas as pd
    Evaluation = apps.get_model("assessment", "Evaluation")
    user_ids = list(cohort.memberships.values_list("user_id", flat=True))
    if not user_ids:
        return {"status": "insufficient_data", "reason": "La cohorte ne contient aucun membre.", "cohort": cohort.name}
    performance_rows = list(Performance.objects.filter(user_id__in=user_ids).values(
        "course_id", "course__title", "average_score", "quiz_count", "exercise_count"
    ))
    evaluations = list(Evaluation.objects.filter(attempt__user_id__in=user_ids).values(
        "attempt__quiz_id", "attempt__quiz__title", "score", "attempt__user_id"
    ))
    by_course = []
    if performance_rows:
        frame = pd.DataFrame(performance_rows)
        grouped = frame.groupby(["course_id", "course__title"], as_index=False).agg(
            learners=("average_score", "count"), average_score=("average_score", "mean"),
            quiz_count=("quiz_count", "sum"), exercise_count=("exercise_count", "sum"))
        by_course = [{"course_id": int(row.course_id), "course": row["course__title"],
                      "learners": int(row.learners), "average_score": round(float(row.average_score), 2),
                      "quiz_count": int(row.quiz_count), "exercise_count": int(row.exercise_count)}
                     for _, row in grouped.iterrows()]
    by_evaluation = []
    if evaluations:
        frame = pd.DataFrame(evaluations)
        grouped = frame.groupby(["attempt__quiz_id", "attempt__quiz__title"], as_index=False).agg(
            attempts=("score", "count"), learners=("attempt__user_id", "nunique"), average_score=("score", "mean"))
        by_evaluation = [{"evaluation_id": int(row["attempt__quiz_id"]), "evaluation": row["attempt__quiz__title"],
                          "attempts": int(row.attempts), "learners": int(row.learners),
                          "average_score": round(float(row.average_score), 2)} for _, row in grouped.iterrows()]
    return {"status": "available" if by_course or by_evaluation else "insufficient_data",
            "cohort": cohort.name, "subject": cohort.subject or None, "members": len(user_ids),
            "by_course": by_course, "by_evaluation": by_evaluation,
            "formula": "Moyennes arithmétiques sur les lignes réelles de la cohorte; aucun score imputé.",
            "sources": ["analytics.CohortMembership", "analytics.Performance", "assessment.Evaluation"]}
