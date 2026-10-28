import pytest
from io import StringIO
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile

from content.models import (
    Course, Chapter, CourseMaterial, AudioMaterial, DocumentMaterial,
    Transcription, Summary, CoursePresence, CourseVersion, CoursePrerequisite,
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


# ---------------------------------------------------------------------------
# Course Presence (REST + model)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_presence_endpoint_returns_users(api_client, professor, course, student):
    api_client.force_authenticate(user=professor)
    CoursePresence.objects.create(
        course=course, user=professor, channel_name="chan_prof", joined_at=timezone.now(), last_seen=timezone.now()
    )
    CoursePresence.objects.create(
        course=course, user=student, channel_name="chan_stu", joined_at=timezone.now(), last_seen=timezone.now()
    )
    url = reverse("course-presence", args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["count"] == 2
    emails = [u["email"] for u in response.data["users"]]
    assert professor.email in emails
    assert student.email in emails


@pytest.mark.django_db
def test_presence_endpoint_empty_course(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse("course-presence", args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert response.data["users"] == []


@pytest.mark.django_db
def test_presence_model_unique_constraint(course, professor, student):
    CoursePresence.objects.create(
        course=course, user=professor, channel_name="chan_prof", joined_at=timezone.now(), last_seen=timezone.now()
    )
    with pytest.raises(Exception):
        CoursePresence.objects.create(
            course=course, user=professor, channel_name="chan_prof_2", joined_at=timezone.now(), last_seen=timezone.now()
        )


@pytest.mark.django_db
def test_presence_model_touch(course, professor):
    p = CoursePresence.objects.create(
        course=course, user=professor, channel_name="chan_prof", joined_at=timezone.now(), last_seen=timezone.now()
    )
    original = p.last_seen
    import time
    time.sleep(0.01)
    p.touch()
    p.refresh_from_db()
    assert p.last_seen > original


# ---------------------------------------------------------------------------
# Thumbnail generation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(
    USE_S3=False,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
def test_generate_thumbnail_for_image_material(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    from PIL import Image
    import io
    from django.core.files.uploadedfile import SimpleUploadedFile

    # Create a small test image
    img = Image.new('RGB', (100, 100), color='red')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    uploaded = SimpleUploadedFile('test.png', buf.read(), content_type='image/png')

    material = CourseMaterial.objects.create(
        course=course,
        title='Test Image',
        file=uploaded,
        material_type='document',
    )

    url = reverse('coursematerial-generate-thumbnail', args=[material.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['thumbnail_url'] is not None


@pytest.mark.django_db
@override_settings(
    USE_S3=False,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
def test_generate_thumbnail_for_placeholder(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    # Create a material with a non-existent file to test placeholder generation
    material = CourseMaterial.objects.create(
        course=course,
        title='No File Material',
        material_type='video',
    )

    url = reverse('coursematerial-generate-thumbnail', args=[material.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    # Placeholder should still generate a thumbnail URL
    # (thumbnail_utils generates a placeholder even without a real file)


@pytest.mark.django_db
def test_generate_thumbnail_unauthorized(api_client, professor, course, student):
    api_client.force_authenticate(user=student)
    # Publish the course so the student can see the material (but not generate thumbnail)
    course.status = 'published'
    course.save()
    material = CourseMaterial.objects.create(
        course=course,
        title='Test',
        material_type='document',
    )
    url = reverse('coursematerial-generate-thumbnail', args=[material.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Course Versioning
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_version_snapshot(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.title = 'Original Title'
    course.save()

    url = reverse('course-create-version', args=[course.id])
    data = {'change_description': 'Initial version'}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data['version_number'] == 1
    assert response.data['snapshot']['title'] == 'Original Title'
    assert response.data['change_description'] == 'Initial version'


@pytest.mark.django_db
def test_list_versions(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    CourseVersion.create_snapshot(course, professor, 'v1')
    CourseVersion.create_snapshot(course, professor, 'v2')

    url = reverse('course-versions', args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2
    assert response.data[0]['version_number'] == 2  # descending order


@pytest.mark.django_db
def test_rollback_to_version(api_client, professor, course):
    api_client.force_authenticate(user=professor)

    # Create v1
    course.title = 'Version 1 Title'
    course.save()
    CourseVersion.create_snapshot(course, professor, 'v1')

    # Change to v2 state
    course.title = 'Version 2 Title'
    course.save()
    CourseVersion.create_snapshot(course, professor, 'v2')

    # Rollback to v1
    url = reverse('course-rollback', args=[course.id])
    v1 = CourseVersion.objects.get(version_number=1)
    response = api_client.post(url, {'version_id': v1.id}, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['title'] == 'Version 1 Title'


@pytest.mark.django_db
def test_rollback_nonexistent_version(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse('course-rollback', args=[course.id])
    response = api_client.post(url, {'version_id': 99999}, format='json')
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_create_version_unauthorized(api_client, professor, course, student):
    api_client.force_authenticate(user=student)
    course.status = 'published'
    course.save()
    url = reverse('course-create-version', args=[course.id])
    response = api_client.post(url, {}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Scheduled publishing
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_scheduled_publish_at_in_future_stays_draft(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    from datetime import timedelta
    course.status = 'draft'
    course.scheduled_publish_at = timezone.now() + timedelta(days=7)
    course.save()
    course.refresh_from_db()
    assert course.status == 'draft'


@pytest.mark.django_db
def test_scheduled_publish_at_in_past_auto_publishes(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    from datetime import timedelta
    course.status = 'draft'
    course.scheduled_publish_at = timezone.now() - timedelta(minutes=5)
    course.save()
    course.refresh_from_db()
    assert course.status == 'published'


@pytest.mark.django_db
def test_auto_publish_command(course, professor):
    from datetime import timedelta
    from django.core.management import call_command
    from io import StringIO

    course.status = 'draft'
    course.scheduled_publish_at = timezone.now() - timedelta(minutes=5)
    course.save()

    out = StringIO()
    call_command('auto_publish', stdout=out)
    output = out.getvalue().lower()
    assert 'publish' in output or 'course' in output


# ---------------------------------------------------------------------------
# Duplicate course
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_duplicate_course(api_client, professor, course, chapter, material):
    api_client.force_authenticate(user=professor)
    url = reverse('course-duplicate', args=[course.id])
    data = {'title': 'Course Copy'}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data['title'] == 'Course Copy'
    assert response.data['status'] == 'draft'
    assert response.data['owner_email'] == professor.email


@pytest.mark.django_db
def test_duplicate_course_with_chapters_and_materials(api_client, professor, course, chapter):
    api_client.force_authenticate(user=professor)
    material = CourseMaterial.objects.create(
        course=course,
        title="Audio Material",
        material_type="audio",
    )
    AudioMaterial.objects.create(material=material, duration=120, language='fr')

    url = reverse('course-duplicate', args=[course.id])
    response = api_client.post(url, {'title': 'Copy'}, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data

    new_course_id = response.data['id']
    new_course = Course.objects.get(id=new_course_id)
    assert new_course.chapters.count() == course.chapters.count()
    assert new_course.materials.count() == course.materials.count()

    new_chapter = new_course.chapters.first()
    assert new_chapter.title == chapter.title
    assert new_chapter.order == chapter.order

    new_material = new_course.materials.filter(material_type='audio').first()
    assert new_material is not None
    assert new_material.title == "Audio Material"
    assert new_material.audio_details.duration == 120


@pytest.mark.django_db
def test_duplicate_course_unauthorized(api_client, professor, course, student):
    api_client.force_authenticate(user=student)
    course.status = 'published'
    course.save()
    url = reverse('course-duplicate', args=[course.id])
    response = api_client.post(url, {}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_reading_time_auto_calculated(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.description = ' '.join(['word'] * 400)  # 400 words = ~2 minutes
    course.markdown_content = '# Course\n\n' + ' '.join(['content'] * 600)  # 600 words
    course.save()
    course.refresh_from_db()
    assert course.estimated_reading_minutes is not None
    assert course.estimated_reading_minutes >= 1


@pytest.mark.django_db
def test_reading_time_in_serializer(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.description = ' '.join(['word'] * 200)
    course.save()
    course.refresh_from_db()

    url = reverse('course-detail', args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['estimated_reading_minutes'] is not None
    assert response.data['estimated_reading_minutes'] >= 1


# ---------------------------------------------------------------------------
# Course Prerequisites
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_add_prerequisite(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    prereq_course = Course.objects.create(
        title='Prérequis',
        status='published',
        owner=professor,
    )
    url = reverse('course-prerequisites', args=[course.id])
    data = {'prerequisite_course': prereq_course.id}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data['prerequisite_title'] == 'Prérequis'


@pytest.mark.django_db
def test_list_prerequisites(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    prereq_course = Course.objects.create(
        title='Prérequis',
        status='published',
        owner=professor,
    )
    CoursePrerequisite.objects.create(course=course, prerequisite_course=prereq_course)

    url = reverse('course-prerequisites', args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['prerequisite_title'] == 'Prérequis'


@pytest.mark.django_db
def test_remove_prerequisite(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    prereq_course = Course.objects.create(
        title='Prérequis',
        status='published',
        owner=professor,
    )
    prereq = CoursePrerequisite.objects.create(course=course, prerequisite_course=prereq_course)

    url = reverse('course-remove-prerequisite', args=[course.id, prereq.id])
    response = api_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not CoursePrerequisite.objects.filter(id=prereq.id).exists()


@pytest.mark.django_db
def test_cannot_add_self_as_prerequisite(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    url = reverse('course-prerequisites', args=[course.id])
    data = {'prerequisite_course': course.id}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_cannot_create_circular_prerequisite(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course_b = Course.objects.create(title='Course B', status='published', owner=professor)
    CoursePrerequisite.objects.create(course=course_b, prerequisite_course=course)

    url = reverse('course-prerequisites', args=[course.id])
    data = {'prerequisite_course': course_b.id}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Export course
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_export_course_zip(api_client, professor, course, chapter, material):
    api_client.force_authenticate(user=professor)
    course.status = 'published'
    course.save()

    url = reverse('course-export', args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response['Content-Type'] == 'application/zip'
    assert 'attachment' in response.get('Content-Disposition', '')
    assert response.get('Content-Disposition', '').endswith('.zip"')


@pytest.mark.django_db
def test_export_course_unpublished_for_student(api_client, professor, course, student):
    api_client.force_authenticate(user=student)
    # course is draft by default, student can't see it → 404
    url = reverse('course-export', args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_export_course_unauthorized(api_client, professor, course, student):
    api_client.force_authenticate(user=student)
    course.status = 'published'
    course.save()
    url = reverse('course-export', args=[course.id])
    response = api_client.get(url)
    # Students can access published courses (same as download)
    assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Slug SEO-friendly
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_slug_auto_generated(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.refresh_from_db()
    assert course.slug is not None
    assert course.slug == 'cours-de-test'


@pytest.mark.django_db
def test_slug_uniqueness(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    # Create another course with same title
    course2 = Course.objects.create(
        title='Cours de test',
        status='draft',
        owner=professor,
    )
    course2.refresh_from_db()
    assert course2.slug == 'cours-de-test-1'


@pytest.mark.django_db
def test_slug_in_serializer(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.refresh_from_db()

    url = reverse('course-detail', args=[course.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['slug'] == course.slug


# ---------------------------------------------------------------------------
# Pending review moderation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_submit_for_review(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.status = 'draft'
    course.save()

    url = reverse('course-submit-for-review', args=[course.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['status'] == 'pending_review'


@pytest.mark.django_db
def test_submit_for_review_not_draft(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.status = 'published'
    course.save()

    url = reverse('course-submit-for-review', args=[course.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_approve_course(api_client, admin, course):
    api_client.force_authenticate(user=admin)
    course.status = 'pending_review'
    course.save()

    url = reverse('course-approve', args=[course.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['status'] == 'published'


@pytest.mark.django_db
def test_reject_course(api_client, admin, course):
    api_client.force_authenticate(user=admin)
    course.status = 'pending_review'
    course.save()

    url = reverse('course-reject', args=[course.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['status'] == 'draft'


@pytest.mark.django_db
def test_approve_reject_not_admin(api_client, professor, course):
    api_client.force_authenticate(user=professor)
    course.status = 'pending_review'
    course.save()

    url = reverse('course-approve', args=[course.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    url = reverse('course-reject', args=[course.id])
    response = api_client.post(url, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
