import React, { useState, useParams, useNavigate, useEffect } from 'react';
import { CheckCircle, Loader2, FileText, Pencil, Trash, Clock } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { EmptyState, LoadingState, ErrorState } from '../../../components/ui/States';
import '../../student/components/courses.css';

export function CourseEditPage() {
  const { id } = useParams();
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [course, setCourse] = useState(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm();

  React.useEffect(() => {
    if (!id || !isBackendApiEnabled) return;
    coursesApi.detail(id).then((data) => {
      setCourse(data);
      reset({
        title: data.title,
        description: data.description,
        level: data.level || 'intermediate',
        language: data.language || 'en',
        content_type: data.content_type || 'document',
        markdown_content: data.markdown_content || '',
        latex_content: data.latex_content || '',
        scheduled_publish_at: data.scheduled_publish_at,
      });
    }).catch(() => {
      setError('Failed to load course details.');
    });
  }, [id, isBackendApiEnabled, reset]);

  const onSubmit = async (data) => {
    setSaving(true);
    setError('');
    setSuccess(false);
    try {
      const payload = {
        title: data.title,
        description: data.description,
        level: data.level,
        language: data.language,
        content_type: data.content_type,
        markdown_content: data.markdown_content || '',
        latex_content: data.latex_content || '',
        scheduled_publish_at: data.scheduled_publish_at,
      };
      await coursesApi.update(id, payload);
      setSuccess(true);
      setTimeout(() => navigate(`/teacher/courses/${id}/edit`), 1500);
    } catch (err) {
      setError('Failed to update course. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <AppShell>
        <PageHeader eyebrow="Course Edit" title="Course Edit" description="Edit course details" />
        <EmptyState title="API Disabled" description="Connect to the backend API to enable course editing." />
      </AppShell>
    );
  }

  if (!course) {
    return (
      <AppShell>
        <PageHeader eyebrow="Course Edit" title="Course Not Found" description="The course you requested could not be found." />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader eyebrow="Course Edit" title={course.title} description="Edit course details" />
      {error && <ErrorState message={error} />}
      {success && <p className="success-text">Course updated successfully!</p>}

      <form className="course-edit-form" onSubmit={handleSubmit(onSubmit)}>
        <div className="form-group">
          <label className="form-label">Course Title <span className="required">*</span></label>
          <input className="form-input" {...register('title', { required: true })} />
          {errors.title && <span className="form-error">{errors.title.message}</span>}
        </div>

        <div className="form-group">
          <label className="form-label">Description <span className="required">*</span></label>
          <textarea className="form-textarea" {...register('description', { required: true })} />
          {errors.description && <span className="form-error">{errors.description.message}</span>}
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Level <span className="required">*</span></label>
            <select className="form-select" {...register('level', { required: true })}>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
              <option value="expert">Expert</option>
            </select>
            {errors.level && <span className="form-error">{errors.level.message}</span>}
          </div>
          <div className="form-group">
            <label className="form-label">Language <span className="required">*</span></label>
            <select className="form-select" {...register('language', { required: true })}>
              <option value="en">English</option>
              <option value="fr">Français</option>
              <option value="es">Español</option>
              <option value="de">Deutsch</option>
            </select>
            {errors.language && <span className="form-error">{errors.language.message}</span>}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Content Type <span className="required">*</span></label>
          <select className="form-select" {...register('content_type', { required: true })}>
            <option value="document">Document</option>
            <option value="audio">Audio</option>
            <option value="video">Video</option>
            <option value="code">Code</option>
            <option value="markdown">Markdown</option>
            <option value="latex">LaTeX</option>
            <option value="mixed">Mixed</option>
            {errors.content_type && <span className="form-error">{errors.content_type.message}</span>}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Markdown Content</label>
          <textarea className="form-textarea" {...register('markdown_content')} rows={4} />
        </div>

        <div className="form-group">
          <label className="form-label">LaTeX Content</label>
          <textarea className="form-textarea" {...register('latex_content')} rows={3} />
        </div>

        <div className="form-group">
          <label className="form-label">Scheduled Publish At</label>
          <input className="form-input" type="datetime-local" {...register('scheduled_publish_at')} />
        </div>

        <div className="form-actions">
          {course.status === 'draft' && (
            <Button type="submit" disabled={saving} className="btn-course-primary">
              {saving ? 'Saving…' : 'Update Course'}
            </Button>
          )}
          {course.status !== 'archived' && (
            <Button
              variant="danger"
              onClick={async () => {
                if (window.confirm('Are you sure you want to archive this course?')) {
                  await coursesApi.archive(id);
                  navigate(-1, { replace: true });
                }
              }}
              disabled={saving}
              className="btn-course-ghost"
            >
              {saving ? 'Archiving…' : 'Archive'}
            </Button>
          )}
          <Button variant="outline" onClick={() => navigate(-1, { replace: true })} disabled={saving} className="btn-course-ghost">
            Cancel
          </Button>
        </div>
      </form>
    </AppShell>
  );
}
