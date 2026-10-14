"""
Tests des étapes 2 (quiz) et 3 (tentatives, correction). Lancer avec :  python manage.py test assessment
Chaque test part d'une base vide : les données sont créées dans setUp.
"""
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from content.models import Course

from .models import Answer, Evaluation, Question, Quiz, QuizAttempt

User = get_user_model()
BASE = '/api/v1/assessment/quizzes/'
FAST_HASHER = ['django.contrib.auth.hashers.MD5PasswordHasher']  # accélère les tests


def make_user(email, role):
    """Crée un utilisateur de test avec le rôle voulu."""
    return User.objects.create_user(
        email=email, username=email.split('@')[0], first_name='T', last_name='T',
        password='Pass12345!x', role=role,
    )


def quiz_payload(course, **overrides):
    """Corps JSON d'un quiz complet et valide : 1 question, 2 choix, 1 correct."""
    payload = {
        'course_id': course.id,
        'title': 'Quiz anglais',
        'difficulty': 'easy',
        'questions': [{
            'prompt': '2 + 2 ?',
            'explanation': 'Parce que 2 + 2 = 4.',
            'choices': [{'text': '4', 'is_correct': True}, {'text': '5'}],
        }],
    }
    payload.update(overrides)
    return payload


@override_settings(PASSWORD_HASHERS=FAST_HASHER)
class QuizApiTests(APITestCase):
    def setUp(self):
        self.course = Course.objects.create(title='Anglais', description='d', level='L1', language='fr')
        self.teacher = make_user('prof@x.com', 'professeur')
        self.other_teacher = make_user('prof2@x.com', 'professeur')
        self.student = make_user('stud@x.com', 'etudiant')
        self.admin = make_user('admin@x.com', 'admin')

    # --- petits raccourcis -------------------------------------------------
    def create_quiz(self, user=None, **overrides):
        self.client.force_authenticate(user or self.teacher)
        return self.client.post(BASE, quiz_payload(self.course, **overrides), format='json')

    def create_published(self, user=None):
        quiz_id = self.create_quiz(user).data['id']
        self.client.post(f'{BASE}{quiz_id}/publish/')
        return quiz_id

    # --- authentification et permissions -----------------------------------
    def test_requires_login(self):
        self.assertEqual(self.client.get(BASE).status_code, 401)

    def test_student_cannot_create(self):
        self.assertEqual(self.create_quiz(self.student).status_code, 403)

    def test_student_cannot_publish_or_edit_or_delete(self):
        quiz_id = self.create_published()
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.post(f'{BASE}{quiz_id}/publish/').status_code, 403)
        self.assertEqual(self.client.patch(f'{BASE}{quiz_id}/', {'title': 'x'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'{BASE}{quiz_id}/').status_code, 403)

    # --- création ----------------------------------------------------------
    def test_teacher_creates_quiz_with_nested_questions(self):
        response = self.create_quiz()
        self.assertEqual(response.status_code, 201)
        data = response.data
        self.assertEqual(data['status'], 'draft')
        self.assertIsInstance(data['id'], str)                      # ids en chaîne
        self.assertEqual(data['course_id'], str(self.course.id))
        self.assertEqual(data['question_count'], 1)
        self.assertEqual(data['scoring']['max_score'], 1)
        choices = data['questions'][0]['choices']
        self.assertEqual([c['text'] for c in choices], ['4', '5'])  # ordre conservé
        self.assertTrue(choices[0]['is_correct'])                   # le prof voit is_correct
        self.assertEqual(Quiz.objects.get().created_by, self.teacher)

    def test_author_cannot_be_forged(self):
        self.create_quiz(created_by=self.admin.id)                  # champ ignoré
        self.assertEqual(Quiz.objects.get().created_by, self.teacher)

    def test_validation_error_uses_contract_format(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(BASE, {'title': 'Sans cours'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Correct the highlighted fields.')
        self.assertIn('course_id', response.data['errors'])

    def test_unknown_course_rejected(self):
        response = self.create_quiz(course_id=9999)
        self.assertEqual(response.status_code, 400)
        self.assertIn('course_id', response.data['errors'])

    # --- visibilité --------------------------------------------------------
    def test_student_sees_only_published_and_never_is_correct(self):
        draft_id = self.create_quiz().data['id']
        published_id = self.create_published()
        self.client.force_authenticate(self.student)

        listing = self.client.get(BASE)
        self.assertEqual(listing.status_code, 200)
        for key in ('results', 'count', 'next'):                    # clés exigées par le contrat
            self.assertIn(key, listing.data)
        self.assertEqual([q['id'] for q in listing.data['results']], [published_id])

        self.assertEqual(self.client.get(f'{BASE}{draft_id}/').status_code, 404)
        detail = self.client.get(f'{BASE}{published_id}/')
        self.assertEqual(detail.status_code, 200)
        question = detail.data['questions'][0]
        self.assertNotIn('explanation', question)
        for choice in question['choices']:
            self.assertEqual(set(choice), {'id', 'text'})           # aucune fuite de la réponse
        self.assertEqual(detail.data['scoring']['type'], 'count')

    def test_teacher_sees_only_own_quizzes_admin_sees_all(self):
        self.create_quiz(self.teacher)
        self.create_quiz(self.other_teacher)
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get(BASE).data['count'], 1)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(BASE).data['count'], 2)

    def test_teacher_cannot_touch_another_teachers_quiz(self):
        quiz_id = self.create_quiz(self.other_teacher).data['id']
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get(f'{BASE}{quiz_id}/').status_code, 404)
        self.assertEqual(self.client.patch(f'{BASE}{quiz_id}/', {'title': 'x'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(f'{BASE}{quiz_id}/publish/').status_code, 404)

    # --- modification et suppression ---------------------------------------
    def test_patch_draft_title_keeps_questions(self):
        quiz_id = self.create_quiz().data['id']
        response = self.client.patch(f'{BASE}{quiz_id}/', {'title': 'Nouveau titre'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Nouveau titre')
        self.assertEqual(response.data['question_count'], 1)

    def test_patch_questions_replaces_the_list(self):
        quiz_id = self.create_quiz().data['id']
        new_questions = [
            {'prompt': 'A ?', 'choices': [{'text': 'a', 'is_correct': True}, {'text': 'b'}]},
            {'prompt': 'B ?', 'choices': [{'text': 'c'}, {'text': 'd', 'is_correct': True}]},
        ]
        response = self.client.patch(f'{BASE}{quiz_id}/', {'questions': new_questions}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([q['prompt'] for q in response.data['questions']], ['A ?', 'B ?'])
        self.assertEqual(response.data['scoring']['max_score'], 2)

    def test_published_quiz_cannot_be_edited_or_deleted(self):
        quiz_id = self.create_published()
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.patch(f'{BASE}{quiz_id}/', {'title': 'x'}, format='json').status_code, 409)
        self.assertEqual(self.client.delete(f'{BASE}{quiz_id}/').status_code, 409)

    def test_delete_draft(self):
        quiz_id = self.create_quiz().data['id']
        self.assertEqual(self.client.delete(f'{BASE}{quiz_id}/').status_code, 204)
        self.assertFalse(Quiz.objects.exists())

    def test_put_is_not_allowed(self):
        quiz_id = self.create_quiz().data['id']
        self.assertEqual(self.client.put(f'{BASE}{quiz_id}/', {}, format='json').status_code, 405)

    # --- publication -------------------------------------------------------
    def test_publish_ok_sets_status_and_date(self):
        quiz_id = self.create_quiz().data['id']
        response = self.client.post(f'{BASE}{quiz_id}/publish/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'published')
        self.assertIsNotNone(response.data['published_at'])

    def test_publish_twice_conflicts(self):
        quiz_id = self.create_published()
        self.assertEqual(self.client.post(f'{BASE}{quiz_id}/publish/').status_code, 409)

    def test_publish_empty_quiz_rejected(self):
        quiz_id = self.create_quiz(questions=[]).data['id']
        response = self.client.post(f'{BASE}{quiz_id}/publish/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Correct the highlighted fields.')
        self.assertIn('questions', response.data['errors'])

    def test_publish_rejects_missing_or_multiple_correct_choices(self):
        no_correct = [{'prompt': 'Q', 'choices': [{'text': 'a'}, {'text': 'b'}]}]
        two_correct = [{'prompt': 'Q', 'choices': [{'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': True}]}]
        one_choice = [{'prompt': 'Q', 'choices': [{'text': 'a', 'is_correct': True}]}]
        for questions in (no_correct, two_correct, one_choice):
            quiz_id = self.create_quiz(questions=questions).data['id']
            response = self.client.post(f'{BASE}{quiz_id}/publish/')
            self.assertEqual(response.status_code, 400, questions)
            self.assertTrue(response.data['errors']['questions'])
            self.assertEqual(Quiz.objects.get(pk=quiz_id).status, 'draft')



# ===========================================================================
# Étape 3 : tentatives, soumission et correction
# ===========================================================================
@override_settings(PASSWORD_HASHERS=FAST_HASHER)
class AttemptApiTests(APITestCase):
    def setUp(self):
        self.course = Course.objects.create(title='Anglais', description='d', level='L1', language='fr')
        self.teacher = make_user('prof@x.com', 'professeur')
        self.student = make_user('stud@x.com', 'etudiant')
        self.other_student = make_user('stud2@x.com', 'etudiant')

        # Quiz publié de 3 questions ; la 1re réponse de chaque question est la bonne.
        self.client.force_authenticate(self.teacher)
        questions = [
            {'prompt': f'Question {n} ?', 'explanation': f'Explication {n}.',
             'choices': [{'text': f'bonne {n}', 'is_correct': True}, {'text': f'fausse {n}'}]}
            for n in (1, 2, 3)
        ]
        self.quiz_id = self.client.post(
            BASE, quiz_payload(self.course, questions=questions), format='json',
        ).data['id']
        self.client.post(f'{BASE}{self.quiz_id}/publish/')
        self.client.force_authenticate(None)

        # Raccourcis : {numéro de question: (id question, id bonne réponse, id mauvaise réponse)}
        self.q = {}
        for index, question in enumerate(Question.objects.filter(quiz_id=self.quiz_id), start=1):
            right, wrong = question.choices.order_by('order')
            self.q[index] = (question.id, right.id, wrong.id)

    # --- raccourcis --------------------------------------------------------
    @property
    def url(self):
        return f'{BASE}{self.quiz_id}/attempts/'

    def start(self, user=None):
        self.client.force_authenticate(user or self.student)
        return self.client.post(self.url)

    def answer_map(self, *picks):
        """picks = ('right'|'wrong'|None) pour les questions 1, 2, 3 -> corps JSON d'un PATCH."""
        result = {}
        for index, pick in enumerate(picks, start=1):
            question_id, right, wrong = self.q[index]
            result[str(question_id)] = {'right': right, 'wrong': wrong, None: None}[pick]
        return {'answers': result}

    # --- accès -------------------------------------------------------------
    def test_requires_login(self):
        self.assertEqual(self.client.post(self.url).status_code, 401)

    def test_teacher_cannot_take_quiz(self):
        self.assertEqual(self.start(self.teacher).status_code, 403)

    def test_cannot_start_on_draft_or_unknown_quiz(self):
        self.client.force_authenticate(self.teacher)
        draft_id = self.client.post(BASE, quiz_payload(self.course), format='json').data['id']
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.post(f'{BASE}{draft_id}/attempts/').status_code, 404)
        self.assertEqual(self.client.post(f'{BASE}9999/attempts/').status_code, 404)

    # --- démarrer ----------------------------------------------------------
    def test_start_creates_attempt_with_explicit_null_answers(self):
        response = self.start()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'in_progress')
        self.assertEqual(response.data['quiz_id'], self.quiz_id)
        self.assertEqual(len(response.data['answers']), 3)
        self.assertTrue(all(value is None for value in response.data['answers'].values()))
        self.assertIsNone(response.data['score'])

    def test_start_twice_returns_the_active_attempt(self):
        first = self.start()
        second = self.client.post(self.url)
        self.assertEqual(second.status_code, 200)             # 200 = tentative existante
        self.assertEqual(second.data['id'], first.data['id'])
        self.assertEqual(QuizAttempt.objects.count(), 1)

    # --- sauvegarder -------------------------------------------------------
    def test_patch_saves_answers_and_keeps_the_others(self):
        attempt_id = self.start().data['id']
        url = f'{self.url}{attempt_id}/'
        first = self.client.patch(url, self.answer_map('right', None, None), format='json')
        self.assertEqual(first.status_code, 200)
        # 2e PATCH : ne mentionne que la question 2 ; la réponse 1 doit rester.
        second = self.client.patch(
            url, {'answers': {str(self.q[2][0]): self.q[2][2]}}, format='json',   # entier OK
        )
        answers = second.data['answers']
        self.assertEqual(answers[str(self.q[1][0])], str(self.q[1][1]))
        self.assertEqual(answers[str(self.q[2][0])], str(self.q[2][2]))
        self.assertIsNone(answers[str(self.q[3][0])])
        # envoyer null efface une réponse
        cleared = self.client.patch(url, self.answer_map(None, 'wrong', None), format='json')
        self.assertIsNone(cleared.data['answers'][str(self.q[1][0])])

    def test_patch_accepts_string_ids(self):
        attempt_id = self.start().data['id']
        body = {'answers': {str(self.q[1][0]): str(self.q[1][1])}}              # tout en chaînes
        response = self.client.patch(f'{self.url}{attempt_id}/', body, format='json')
        self.assertEqual(response.status_code, 200)

    def test_patch_rejects_foreign_question_or_choice(self):
        attempt_id = self.start().data['id']
        url = f'{self.url}{attempt_id}/'
        bad_question = self.client.patch(url, {'answers': {'99999': self.q[1][1]}}, format='json')
        self.assertEqual(bad_question.status_code, 400)
        self.assertEqual(bad_question.data['detail'], 'Correct the highlighted fields.')
        self.assertIn('99999', bad_question.data['errors']['answers'])
        # un choix de la question 2 envoyé pour la question 1
        bad_choice = self.client.patch(url, {'answers': {str(self.q[1][0]): self.q[2][1]}}, format='json')
        self.assertEqual(bad_choice.status_code, 400)
        self.assertEqual(self.client.patch(url, {}, format='json').status_code, 400)   # "answers" obligatoire
        self.assertFalse(Answer.objects.exists())                                       # rien enregistré

    def test_other_student_cannot_see_or_change_my_attempt(self):
        attempt_id = self.start().data['id']
        self.client.force_authenticate(self.other_student)
        url = f'{self.url}{attempt_id}/'
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, self.answer_map('right', 'right', 'right'), format='json').status_code, 404)
        self.assertEqual(self.client.post(f'{url}submit/').status_code, 404)
        self.assertEqual(self.client.get(f'{url}evaluation/').status_code, 404)

    # --- soumettre et corriger ---------------------------------------------
    def test_submit_all_correct(self):
        attempt_id = self.start().data['id']
        url = f'{self.url}{attempt_id}/'
        self.client.patch(url, self.answer_map('right', 'right', 'right'), format='json')
        response = self.client.post(f'{url}submit/')
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual((data['score'], data['correct_answers'], data['total_questions']), (3, 3, 3))
        self.assertIsInstance(data['score'], int)                  # compte, pas pourcentage
        self.assertTrue(all(item['is_correct'] for item in data['question_feedback']))
        self.assertIn('Excellent', data['feedback'])
        self.assertEqual(QuizAttempt.objects.get().status, 'submitted')
        self.assertIsNotNone(QuizAttempt.objects.get().submitted_at)

    def test_submit_mixed_wrong_and_unanswered(self):
        attempt_id = self.start().data['id']
        url = f'{self.url}{attempt_id}/'
        self.client.patch(url, self.answer_map('right', 'wrong', None), format='json')
        data = self.client.post(f'{url}submit/').data
        self.assertEqual((data['score'], data['correct_answers'], data['total_questions']), (1, 1, 3))
        verdicts = [item['is_correct'] for item in data['question_feedback']]
        self.assertEqual(verdicts, [True, False, False])
        feedback = {item['question_id']: item['feedback'] for item in data['question_feedback']}
        self.assertIn('Incorrect', feedback[str(self.q[2][0])])
        self.assertIn('bonne 2', feedback[str(self.q[2][0])])           # indique la bonne réponse
        self.assertIn('Explication 2.', feedback[str(self.q[2][0])])    # + l'explication du prof
        self.assertIn('Not answered', feedback[str(self.q[3][0])])
        self.assertEqual(data['question_feedback'][0]['question'], 'Question 1 ?')
        self.assertTrue(any('Question 2' in step for step in data['next_steps']))
        # une ligne Answer par question, y compris la non répondue
        self.assertEqual(Answer.objects.count(), 3)
        unanswered = Answer.objects.get(question_id=self.q[3][0])
        self.assertIsNone(unanswered.selected_choice_id)

    def test_submit_with_answers_in_body(self):
        attempt_id = self.start().data['id']
        body = self.answer_map('right', 'right', 'wrong')
        response = self.client.post(f'{self.url}{attempt_id}/submit/', body, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['correct_answers'], 2)

    def test_submit_with_invalid_answers_in_body_changes_nothing(self):
        attempt_id = self.start().data['id']
        response = self.client.post(f'{self.url}{attempt_id}/submit/', {'answers': {'99999': 1}}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(QuizAttempt.objects.get().status, 'in_progress')
        self.assertFalse(Evaluation.objects.exists())

    def test_cannot_submit_or_patch_twice(self):
        attempt_id = self.start().data['id']
        url = f'{self.url}{attempt_id}/'
        self.client.post(f'{url}submit/')
        self.assertEqual(self.client.post(f'{url}submit/').status_code, 409)
        self.assertEqual(self.client.patch(url, self.answer_map('right', 'right', 'right'), format='json').status_code, 409)
        self.assertEqual(Evaluation.objects.count(), 1)

    # --- évaluation --------------------------------------------------------
    def test_evaluation_unavailable_before_submit_then_readable(self):
        attempt_id = self.start().data['id']
        url = f'{self.url}{attempt_id}/'
        self.assertEqual(self.client.get(f'{url}evaluation/').status_code, 404)
        self.client.patch(url, self.answer_map('right', 'wrong', 'right'), format='json')
        submitted = self.client.post(f'{url}submit/').data
        read = self.client.get(f'{url}evaluation/')
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.data['score'], submitted['score'])
        self.assertEqual(read.data['attempt_id'], attempt_id)
        self.assertEqual(read.data['quiz_id'], self.quiz_id)

    # --- historique ----------------------------------------------------------
    def test_new_attempt_allowed_after_submission(self):
        first_id = self.start().data['id']
        self.client.post(f'{self.url}{first_id}/submit/')
        second = self.client.post(self.url)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(second.data['id'], first_id)

    def test_list_shows_only_my_attempts_newest_first_with_score(self):
        first_id = self.start().data['id']
        self.client.patch(f'{self.url}{first_id}/', self.answer_map('right', 'right', 'wrong'), format='json')
        self.client.post(f'{self.url}{first_id}/submit/')
        second_id = self.client.post(self.url).data['id']
        self.start(self.other_student)                                     # tentative d'un autre étudiant

        self.client.force_authenticate(self.student)
        listing = self.client.get(self.url)
        self.assertEqual(listing.status_code, 200)
        for key in ('results', 'count', 'next'):
            self.assertIn(key, listing.data)
        self.assertEqual([a['id'] for a in listing.data['results']], [second_id, first_id])
        self.assertEqual(listing.data['results'][1]['score'], 2)           # tentative corrigée
        self.assertIsNone(listing.data['results'][0]['score'])             # tentative en cours