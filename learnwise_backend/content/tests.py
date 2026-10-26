import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from content.models import (
    Course, Chapter, CourseMaterial, AudioMaterial, DocumentMaterial,
    Transcription, Summary,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def professor(db):
    return User.objects.create_user(
        email="prof@learnwise.local",
        username="prof",
        first_name="Prof",
        last_name="Essais",
        role="professeur",
        password="ProfPass123!",
        email_verified=True,
    )


@pytest.fixture
def student(db):
    return User.objects.create_user(
        email="etudiant@learnwise.local",
        username="etudiant",
        first_name="Étu",
        last_name="Tests",
        role="etudiant",
        password="EtudPass123!",
        email_verified=True,
    )


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(
        email="admin@learnwise.local",
        username="admin",
        password="AdminPass123!",
        email_verified=True,
    )


@pytest.fixture
def course(professor):
    return Course.objects.create(
        title="Cours de test",
        description="Description du cours",
        level="débutant",
        language="fr",
        status="draft",
        content_type="document",
        owner=professor,
    )


@pytest.fixture
def material(course):
    return CourseMaterial.objects.create(
        course=course,
        title="Matériau test",
        material_type="document",
    )


# ---------------------------------------------------------------------------
# Authentification / permissions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_unauthenticated_cannot_access_courses(api_client):
    url = reverse("course-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_professor_can_list_courses(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("course-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) >= 1


@pytest.mark.django_db
def test_student_sees_only_published_courses(api_client, student, course, professor):
    # Le cours est en draft, l'étudiant ne doit pas le voir
    api_client.force_authenticate(user=student)
    url = reverse("course-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 0

    # Le professeur publie le cours
    course.status = "published"
    course.save()
    response = api_client.get(url)
    assert len(response.data["results"]) == 1


# ---------------------------------------------------------------------------
# Course CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_professor_create_course(api_client, professor):
    api_client.force_authenticate(user=professor)
    url = reverse("course-list")
    data = {
        "title": "Nouveau cours",
        "description": "Un cours complet",
        "level": "intermédiaire",
        "language": "fr",
        "status": "draft",
        "content_type": "markdown",
        "markdown_content": "# Mon cours\n\nContenu en markdown",
        "latex_content": "",
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["title"] == "Nouveau cours"
    assert response.data["owner_email"] == professor.email


@pytest.mark.django_db
def test_student_cannot_create_course(api_client, student):
    api_client.force_authenticate(user=student)
    url = reverse("course-list")
    data = {"title": "Cours étudiant", "status": "draft", "content_type": "document"}
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_professor_retrieve_course(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("course-detail", args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == course.title


@pytest.mark.django_db
def test_professor_update_course(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("course-detail", args=[course.id])
    data = {"title": "Titre modifié", "status": "published"}
    response = api_client.patch(url, data, format="json")
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["title"] == "Titre modifié"
    assert response.data["status"] == "published"


@pytest.mark.django_db
def test_professor_delete_course(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("course-detail", args=[course.id])
    response = api_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Course.objects.filter(id=course.id).exists()


@pytest.mark.django_db
def test_other_professor_cannot_modify_course(api_client, course):
    other_prof = User.objects.create_user(
        email="autre@learnwise.local",
        username="autreprof",
        role="professeur",
        password="Pass123!",
        email_verified=True,
    )
    api_client.force_authenticate(user=other_prof)
    url = reverse("course-detail", args=[course.id])
    response = api_client.patch(url, {"title": "Hack"}, format="json")
    assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Publish / Archive actions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_publish_course(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("course-publish", args=[course.id])
    response = api_client.post(url, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "published"


@pytest.mark.django_db
def test_archive_course(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.status = "published"
    course.save()
    url = reverse("course-archive", args=[course.id])
    response = api_client.post(url, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "archived"


@pytest.mark.django_db
def test_course_stats(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("course-stats")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "total" in response.data
    assert "draft" in response.data
    assert "published" in response.data
    assert "archived" in response.data


# ---------------------------------------------------------------------------
# CourseMaterial CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_professor_create_material(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("coursematerial-list")
    data = {
        "course": course.id,
        "title": "Support PDF",
        "material_type": "document",
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["title"] == "Support PDF"


@pytest.mark.django_db
def test_student_sees_materials_of_published_course_only(api_client, student, course, professor):
    course.status = "published"
    course.save()
    mat = CourseMaterial.objects.create(
        course=course, title="Matériel publié", material_type="document"
    )
    draft_course = Course.objects.create(
        title="Cours brouillon", status="draft", owner=professor
    )
    CourseMaterial.objects.create(
        course=draft_course, title="Matériel brouillon", material_type="document"
    )

    api_client.force_authenticate(user=student)
    url = reverse("coursematerial-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    titles = [item["title"] for item in response.data["results"]]
    assert "Matériel publié" in titles
    assert "Matériel brouillon" not in titles


@pytest.mark.django_db
def test_material_filter_by_course(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("coursematerial-list")
    response = api_client.get(url, {"course": course.id})
    assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# AudioMaterial / DocumentMaterial / Transcription / Summary CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_audio_material_crud(api_client, professor, course, material):
    api_client.force_authenticate(user=professor)
    # Create
    url = reverse("audiomaterial-list")
    data = {"material": material.id, "duration": 120, "language": "fr"}
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    audio_id = response.data["id"]

    # Retrieve
    detail_url = reverse("audiomaterial-detail", args=[audio_id])
    response = api_client.get(detail_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["duration"] == 120

    # Update
    response = api_client.patch(detail_url, {"duration": 180}, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["duration"] == 180

    # Delete
    response = api_client.delete(detail_url)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_document_material_crud(api_client, professor, course, material):
    api_client.force_authenticate(user=professor)
    url = reverse("documentmaterial-list")
    data = {"material": material.id, "page_count": 10, "mime_type": "application/pdf"}
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data

    detail_url = reverse("documentmaterial-detail", args=[response.data["id"]])
    response = api_client.patch(detail_url, {"page_count": 15}, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["page_count"] == 15


@pytest.mark.django_db
def test_transcription_crud(api_client, professor, course, material):
    api_client.force_authenticate(user=professor)
    url = reverse("transcription-list")
    data = {
        "material": material.id,
        "content": "Contenu de la transcription",
        "language": "fr",
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data

    detail_url = reverse("transcription-detail", args=[response.data["id"]])
    response = api_client.get(detail_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["content"] == "Contenu de la transcription"


@pytest.mark.django_db
def test_summary_crud(api_client, professor, course, material):
    api_client.force_authenticate(user=professor)
    url = reverse("summary-list")
    data = {
        "material": material.id,
        "content": "Résumé du cours",
        "summary_type": "general",
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data

    detail_url = reverse("summary-detail", args=[response.data["id"]])
    response = api_client.get(detail_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["summary_type"] == "general"


# ---------------------------------------------------------------------------
# VideoMaterial CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_video_material_crud(api_client, professor, course, material):
    api_client.force_authenticate(user=professor)
    url = reverse("videomaterial-list")
    data = {
        "material": material.id,
        "duration": 300,
        "resolution": "1920x1080",
        "language": "fr",
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    video_id = response.data["id"]

    detail_url = reverse("videomaterial-detail", args=[video_id])
    response = api_client.get(detail_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["duration"] == 300
    assert response.data["resolution"] == "1920x1080"

    response = api_client.patch(detail_url, {"duration": 360}, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["duration"] == 360

    response = api_client.delete(detail_url)
    assert response.status_code == status.HTTP_204_NO_CONTENT


# ---------------------------------------------------------------------------
# Filtering / search
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_course_filter_by_status_and_level(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    Course.objects.create(
        title="Autre cours",
        status="published",
        level="avancé",
        language="fr",
        owner=professor,
    )
    url = reverse("course-list")
    response = api_client.get(url, {"status": "draft", "level": "débutant"})
    assert response.status_code == status.HTTP_200_OK
    for item in response.data["results"]:
        assert item["status"] == "draft"
        assert item["level"] == "débutant"


@pytest.mark.django_db
def test_course_search(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("course-list")
    response = api_client.get(url, {"search": "Cours de test"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) >= 1


# ---------------------------------------------------------------------------
# Chapter CRUD
# ---------------------------------------------------------------------------

@pytest.fixture
def chapter(course):
    return Chapter.objects.create(
        course=course,
        title="Chapitre 1",
        description="Premier chapitre",
        order=1,
    )


@pytest.mark.django_db
def test_professor_create_chapter(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("chapter-list")
    data = {
        "course": course.id,
        "title": "Chapitre 2",
        "description": "Deuxième chapitre",
        "order": 2,
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["title"] == "Chapitre 2"
    assert response.data["order"] == 2


@pytest.mark.django_db
def test_student_cannot_create_chapter(api_client, student, course):
    api_client.force_authenticate(user=student)
    url = reverse("chapter-list")
    data = {"course": course.id, "title": "Chapitre étudiant", "order": 1}
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_professor_retrieve_chapter(api_client, professor, chapter):
    api_client.force_authenticate(user=professor)
    url = reverse("chapter-detail", args=[chapter.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == chapter.title


@pytest.mark.django_db
def test_professor_update_chapter(api_client, professor, chapter):
    api_client.force_authenticate(user=professor)
    url = reverse("chapter-detail", args=[chapter.id])
    data = {"title": "Chapitre modifié", "order": 5}
    response = api_client.patch(url, data, format="json")
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["title"] == "Chapitre modifié"
    assert response.data["order"] == 5


@pytest.mark.django_db
def test_professor_delete_chapter(api_client, professor, chapter):
    api_client.force_authenticate(user=professor)
    url = reverse("chapter-detail", args=[chapter.id])
    response = api_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Chapter.objects.filter(id=chapter.id).exists()


@pytest.mark.django_db
def test_student_sees_chapters_of_published_course_only(api_client, student, course, professor):
    course.status = "published"
    course.save()
    Chapter.objects.create(course=course, title="Chapitre publié", order=1)
    draft_course = Course.objects.create(
        title="Cours brouillon", status="draft", owner=professor
    )
    Chapter.objects.create(course=draft_course, title="Chapitre brouillon", order=1)

    api_client.force_authenticate(user=student)
    url = reverse("chapter-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    titles = [item["title"] for item in response.data["results"]]
    assert "Chapitre publié" in titles
    assert "Chapitre brouillon" not in titles


@pytest.mark.django_db
def test_chapter_filter_by_course(api_client, professor, course, chapter):
    api_client.force_authenticate(user=professor)
    url = reverse("chapter-list")
    response = api_client.get(url, {"course": course.id})
    assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Material ↔ Chapter association
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_material_can_be_attached_to_chapter(api_client, professor, course, chapter):
    api_client.force_authenticate(user=professor)
    url = reverse("coursematerial-list")
    data = {
        "course": course.id,
        "chapter": chapter.id,
        "title": "Matériau du chapitre",
        "material_type": "document",
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["chapter"] == chapter.id
    assert response.data["chapter_title"] == chapter.title


@pytest.mark.django_db
def test_material_filter_by_chapter(api_client, professor, course, chapter):
    api_client.force_authenticate(user=professor)
    CourseMaterial.objects.create(
        course=course, chapter=chapter, title="Matériau chapitre", material_type="document"
    )
    url = reverse("coursematerial-list")
    response = api_client.get(url, {"chapter": chapter.id})
    assert response.status_code == status.HTTP_200_OK
    for item in response.data["results"]:
        assert item["chapter"] == chapter.id


# ---------------------------------------------------------------------------
# Admin access
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_can_access_all(api_client, admin, course):
    api_client.force_authenticate(user=admin)
    url = reverse("course-detail", args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
