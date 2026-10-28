"""Contexte du cours pour des reponses ancrees dans les sources.

Lit les Transcription et Summary du module `content` pour fournir un contexte
factual aux reponses de l'assistant, avec citations.
"""
import logging

from content.models import CourseMaterial

logger = logging.getLogger(__name__)


def build_context(course_id=None, material_ids=None):
    """Retourne (texte_de_contexte, citations).

    citations : liste de { id, title, type, excerpt }
    """
    context_parts = []
    citations = []

    # Recuperer les materiaux pertinents
    materials_qs = CourseMaterial.objects.all()
    if course_id:
        materials_qs = materials_qs.filter(course_id=course_id)
    if material_ids:
        materials_qs = materials_qs.filter(id__in=material_ids)

    materials = materials_qs.select_related('course').prefetch_related(
        'transcriptions', 'summaries'
    )[:10]

    for material in materials:
        course_title = material.course.title if material.course else 'Cours inconnu'

        # Transcriptions
        for transcription in material.transcriptions.all()[:1]:
            excerpt = transcription.content[:800]
            context_parts.append(
                f"[Source: {course_title} - {material.title} (transcription)]\n{excerpt}"
            )
            citations.append({
                'id': str(material.id),
                'title': material.title,
                'type': 'transcription',
                'course': course_title,
                'excerpt': excerpt[:200] + ('...' if len(excerpt) > 200 else ''),
            })

        # Resumes
        for summary in material.summaries.all()[:1]:
            excerpt = summary.content[:800]
            context_parts.append(
                f"[Source: {course_title} - {material.title} (resume)]\n{excerpt}"
            )
            citations.append({
                'id': str(material.id),
                'title': material.title,
                'type': 'summary',
                'course': course_title,
                'excerpt': excerpt[:200] + ('...' if len(excerpt) > 200 else ''),
            })

    context = '\n\n'.join(context_parts)
    return context, citations
