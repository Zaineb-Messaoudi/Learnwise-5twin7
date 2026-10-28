"""
Correction d'une tentative de quiz (et d'une réponse d'exercice) : score et feedback.

Règles (celles renvoyées dans `scoring` par le détail du quiz) :
- 1 point par bonne réponse, aucun retrait pour une mauvaise réponse ;
- une question sans réponse compte comme fausse ;
- `score` et `correct_answers` sont des COMPTES, pas des pourcentages.

Les textes destinés à l'étudiant sont regroupés ici (constantes) pour
pouvoir les traduire facilement plus tard.
"""
from django.db import transaction
from django.utils import timezone

from .models import Answer, Evaluation, QuizAttempt

# --- Textes affichés à l'étudiant -------------------------------------------
TXT_CORRECT = 'Correct.'
TXT_WRONG = 'Incorrect. The correct answer is: {answer}.'
TXT_UNANSWERED = 'Not answered. The correct answer is: {answer}.'
TXT_NO_CORRECT_CHOICE = 'This question has no correct answer configured.'
TXT_EXCELLENT = 'Excellent work! You have mastered this quiz.'
TXT_GOOD = 'Good effort. A few points are worth reviewing.'
TXT_KEEP_GOING = 'Keep practicing: review the course material and try again.'
TXT_STEP_REVIEW = 'Review: {prompt}'
TXT_STEP_NEXT = 'Move on to a harder quiz or a new topic.'
TXT_STEP_RETRY = 'Retake this quiz once you have reviewed the points above.'


def _question_feedback(question, correct_choice, selected_id, is_correct):
    """Texte de feedback d'une question : verdict + bonne réponse + explication du professeur."""
    if correct_choice is None:
        verdict = TXT_NO_CORRECT_CHOICE
    elif is_correct:
        verdict = TXT_CORRECT
    elif selected_id is None:
        verdict = TXT_UNANSWERED.format(answer=correct_choice.text)
    else:
        verdict = TXT_WRONG.format(answer=correct_choice.text)
    return f'{verdict} {question.explanation}'.strip()


def _overall_feedback(correct, total):
    """Message global selon la proportion de bonnes réponses."""
    ratio = correct / total if total else 0
    if ratio >= 0.8:
        return TXT_EXCELLENT
    if ratio >= 0.5:
        return TXT_GOOD
    return TXT_KEEP_GOING


def grade_exercise(exercise, selected_choice):
    """
    Corrige UNE réponse à un exercice (pas de tentative : chaque soumission est indépendante).
    Renvoie (is_correct, feedback) ; `exercise.choices` doit être préchargé.
    """
    correct_choice = next((c for c in exercise.choices.all() if c.is_correct), None)
    is_correct = correct_choice is not None and selected_choice.id == correct_choice.id
    if correct_choice is None:
        verdict = TXT_NO_CORRECT_CHOICE
    elif is_correct:
        verdict = TXT_CORRECT
    else:
        verdict = TXT_WRONG.format(answer=correct_choice.text)
    return is_correct, f'{verdict} {exercise.explanation}'.strip()


@transaction.atomic
def evaluate_attempt(attempt):
    """
    Corrige la tentative, enregistre une ligne Answer par question
    (y compris les questions sans réponse), crée l'Evaluation et passe
    la tentative à "submitted". Renvoie l'Evaluation.
    """
    questions = list(attempt.quiz.questions.prefetch_related('choices'))
    existing = {answer.question_id: answer for answer in attempt.answers.all()}

    correct_count = 0
    question_feedback = []
    next_steps = []

    for question in questions:
        choices = list(question.choices.all())
        correct_choice = next((c for c in choices if c.is_correct), None)
        answer = existing.get(question.id) or Answer(attempt=attempt, question=question)

        selected_id = answer.selected_choice_id  # None = non répondu
        is_correct = correct_choice is not None and selected_id == correct_choice.id
        answer.is_correct = is_correct
        answer.save()

        if is_correct:
            correct_count += 1
        else:
            next_steps.append(TXT_STEP_REVIEW.format(prompt=question.prompt))

        question_feedback.append({
            'question_id': str(question.id),   # ids en chaîne (contrat)
            'question': question.prompt,
            'is_correct': is_correct,
            'feedback': _question_feedback(question, correct_choice, selected_id, is_correct),
        })

    total = len(questions)
    if correct_count == total:
        next_steps.append(TXT_STEP_NEXT)
    else:
        next_steps.append(TXT_STEP_RETRY)

    evaluation = Evaluation.objects.create(
        attempt=attempt,
        score=correct_count,
        correct_answers=correct_count,
        total_questions=total,
        feedback=_overall_feedback(correct_count, total),
        question_feedback=question_feedback,
        next_steps=next_steps,
    )

    attempt.status = QuizAttempt.Status.SUBMITTED
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=['status', 'submitted_at'])
    return evaluation