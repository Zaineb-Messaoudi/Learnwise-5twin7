"""Tests pour le module ai_assistant."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from .models import (
    AssistantSession,
    AssistantMessage,
    ProcessingStatus,
)

User = get_user_model()


class AssistantSessionCRUDTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='etudiant@test.com',
            username='etudiant',
            password='testpass123',
            first_name='Jean',
            last_name='Dupont',
            role='etudiant',
            email_verified=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_session(self):
        response = self.client.post('/api/v1/assistant/sessions/', {
            'title': 'Ma session de test',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AssistantSession.objects.count(), 1)
        session = AssistantSession.objects.first()
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.title, 'Ma session de test')
        self.assertEqual(session.status, 'active')

    def test_list_sessions(self):
        AssistantSession.objects.create(user=self.user, title='Session 1')
        AssistantSession.objects.create(user=self.user, title='Session 2')
        response = self.client.get('/api/v1/assistant/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_retrieve_session(self):
        session = AssistantSession.objects.create(user=self.user, title='Session test')
        response = self.client.get(f'/api/v1/assistant/sessions/{session.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(session.id))

    def test_update_session(self):
        session = AssistantSession.objects.create(user=self.user, title='Ancien titre')
        response = self.client.patch(
            f'/api/v1/assistant/sessions/{session.id}/',
            {'title': 'Nouveau titre'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.title, 'Nouveau titre')

    def test_delete_session(self):
        session = AssistantSession.objects.create(user=self.user, title='A supprimer')
        response = self.client.delete(f'/api/v1/assistant/sessions/{session.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AssistantSession.objects.count(), 0)

    def test_cannot_access_other_user_session(self):
        other_user = User.objects.create_user(
            email='autre@test.com',
            username='autre',
            password='testpass123',
            role='etudiant',
        )
        session = AssistantSession.objects.create(user=other_user, title='Session autre')
        response = self.client.get(f'/api/v1/assistant/sessions/{session.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MessageCRUDTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='etudiant@test.com',
            username='etudiant',
            password='testpass123',
            role='etudiant',
            email_verified=True,
        )
        self.session = AssistantSession.objects.create(user=self.user, title='Session')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_message(self):
        response = self.client.post(
            f'/api/v1/assistant/sessions/{self.session.id}/messages/',
            {'content': 'Question de test'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AssistantMessage.objects.count(), 2)  # user + assistant

    def test_list_messages(self):
        AssistantMessage.objects.create(session=self.session, role='user', content='Q1')
        AssistantMessage.objects.create(session=self.session, role='assistant', content='R1')
        response = self.client.get(
            f'/api/v1/assistant/sessions/{self.session.id}/messages/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_retrieve_message(self):
        message = AssistantMessage.objects.create(
            session=self.session, role='assistant', content='Reponse'
        )
        response = self.client.get(f'/api/v1/assistant/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Reponse')

    def test_cannot_access_other_user_message(self):
        other_user = User.objects.create_user(
            email='autre@test.com',
            username='autre',
            password='testpass123',
            role='etudiant',
        )
        other_session = AssistantSession.objects.create(user=other_user, title='Session autre')
        message = AssistantMessage.objects.create(
            session=other_session, role='assistant', content='Reponse privee'
        )
        response = self.client.get(f'/api/v1/assistant/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ExplanationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='etudiant@test.com',
            username='etudiant',
            password='testpass123',
            role='etudiant',
            email_verified=True,
        )
        self.session = AssistantSession.objects.create(user=self.user, title='Session')
        self.message = AssistantMessage.objects.create(
            session=self.session,
            role='assistant',
            content='Contenu de la reponse a expliquer.',
            status=ProcessingStatus.COMPLETED,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_explanation(self):
        response = self.client.post(
            f'/api/v1/assistant/messages/{self.message.id}/explanation/',
            {'difficulty_level': 'beginner'},
        )
        # Peut retourner 502 si Gemini n'est pas configure en test
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_502_BAD_GATEWAY])


class IllustrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='etudiant@test.com',
            username='etudiant',
            password='testpass123',
            role='etudiant',
            email_verified=True,
        )
        self.session = AssistantSession.objects.create(user=self.user, title='Session')
        self.message = AssistantMessage.objects.create(
            session=self.session,
            role='assistant',
            content='Contenu pour illustration.',
            status=ProcessingStatus.COMPLETED,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_illustration(self):
        response = self.client.post(
            f'/api/v1/assistant/messages/{self.message.id}/illustrations/',
            {'prompt': 'Un diagramme pedagogique'},
        )
        # Peut retourner 502 si aucun fournisseur d'image n'est configure
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_502_BAD_GATEWAY])


class VoiceQuestionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='etudiant@test.com',
            username='etudiant',
            password='testpass123',
            role='etudiant',
            email_verified=True,
        )
        self.session = AssistantSession.objects.create(user=self.user, title='Session')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_voice_question(self):
        # Test sans fichier audio -> 400
        response = self.client.post(
            f'/api/v1/assistant/sessions/{self.session.id}/voice-questions/',
            {},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
