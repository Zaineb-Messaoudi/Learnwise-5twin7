"""
Tests de l'étape 2 (quiz). Lancer avec :  python manage.py test assessment
Chaque test part d'une base vide : les données sont créées dans setUp.
"""
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from content.models import Course

from .models import Quiz

User = get_user_model()
BASE = '/api/v1/assessment/quizzes/'


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