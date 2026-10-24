"""
Service de génération : texte source, exécution d'un job en arrière-plan, expiration.

Fonctionnement (le frontend fait du polling) :
    POST /generations/  -> crée un job "queued" et lance le travail en arrière-plan
    GET  /generations/<id>/ -> "queued" / "processing" / "completed" (avec result) / "failed"

Le travail tourne dans un thread du serveur : pas de Celery ni de Redis à installer.
Limite assumée : si le serveur redémarre en plein calcul, le job reste bloqué ; il est alors
marqué "failed" automatiquement au bout de STALE_AFTER (voir fail_stale_jobs).
"""
import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.db import connections
from django.utils import timezone

from content.models import CourseMaterial

from . import ai_client
from .models import GenerationJob

logger = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 20000          # texte envoyé à l'IA (au-delà, on tronque)
MAX_ACTIVE_JOBS_PER_USER = 3      # protège le quota de la clé API (ou la machine, avec Ollama)
STALE_AFTER = timedelta(minutes=10)   # un modèle local (Ollama) peut être lent
ACTIVE_STATUSES = (GenerationJob.Status.QUEUED, GenerationJob.Status.PROCESSING)

MSG_TIMEOUT = 'The generation took too long and was cancelled. Please try again.'
MSG_UNEXPECTED = 'Something went wrong during the generation. Please try again.'


def _latest_text(related_manager):
    """Contenu non vide le plus récent d'une relation (transcriptions ou résumés), sinon ''."""
    for item in related_manager.order_by('-created_at', '-id'):
        if item.content and item.content.strip():
            return item.content.strip()
    return ''


def material_text(course, material_ids):
    """
    Texte des supports choisis (lecture seule dans l'app `content`) : pour chaque support,
    sa transcription, à défaut son résumé. Renvoie '' si aucun n'a encore de texte.
    """
    chunks = []
    materials = CourseMaterial.objects.filter(course=course, id__in=material_ids).order_by('id')
    for material in materials:
        text = _latest_text(material.transcriptions) or _latest_text(material.summaries)
        if text:
            chunks.append(f'## {material.title}\n{text}')
    return '\n\n'.join(chunks)


def build_source_text(job):
    """Texte final envoyé à l'IA : le texte saisi + le contenu des supports choisis."""
    parts = [job.source_text.strip(), material_text(job.course, job.material_ids)]
    return '\n\n'.join(part for part in parts if part)[:MAX_SOURCE_CHARS]


def fail_stale_jobs():
    """Marque "failed" les jobs restés actifs trop longtemps (serveur redémarré, thread perdu)."""
    now = timezone.now()
    GenerationJob.objects.filter(
        status__in=ACTIVE_STATUSES, created_at__lt=now - STALE_AFTER,
    ).update(status=GenerationJob.Status.FAILED, error_message=MSG_TIMEOUT, finished_at=now)


def run_generation(job_id):
    """Exécute un job : appelle l'IA et enregistre le résultat ou l'erreur."""
    job = GenerationJob.objects.select_related('course').filter(pk=job_id).first()
    if job is None:
        return
    # Le passage queued -> processing ne réussit qu'une fois : évite un double traitement.
    started = GenerationJob.objects.filter(
        pk=job_id, status=GenerationJob.Status.QUEUED,
    ).update(status=GenerationJob.Status.PROCESSING)
    if not started:
        return

    try:
        questions = ai_client.generate_questions(
            source_text=build_source_text(job),
            course=job.course,
            kind=job.kind,
            count=job.question_count,
            difficulty=job.difficulty,
        )
        changes = {
            'status': GenerationJob.Status.COMPLETED,
            'result': {'questions': questions},
        }
    except ai_client.GenerationError as error:
        changes = {'status': GenerationJob.Status.FAILED, 'error_message': error.user_message}
    except Exception:
        # Bug inattendu : le détail va dans les logs, le professeur ne voit qu'un message neutre.
        logger.exception('Unexpected error in generation job %s', job_id)
        changes = {'status': GenerationJob.Status.FAILED, 'error_message': MSG_UNEXPECTED}

    # Mise à jour conditionnelle : si le job a expiré entre-temps (fail_stale_jobs),
    # un thread très en retard n'écrase pas ce statut.
    GenerationJob.objects.filter(pk=job_id, status=GenerationJob.Status.PROCESSING).update(
        finished_at=timezone.now(), **changes,
    )


def _run_in_thread(job_id):
    try:
        run_generation(job_id)
    finally:
        connections.close_all()  # chaque thread a sa propre connexion à la base : on la ferme


def dispatch(job):
    """Lance le job : en arrière-plan (normal) ou tout de suite (tests : ASSESSMENT_GENERATION_ASYNC=False)."""
    if getattr(settings, 'ASSESSMENT_GENERATION_ASYNC', True):
        threading.Thread(target=_run_in_thread, args=(job.pk,), daemon=True).start()
    else:
        run_generation(job.pk)