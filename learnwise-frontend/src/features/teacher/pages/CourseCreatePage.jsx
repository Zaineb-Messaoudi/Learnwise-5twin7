import React, { useState, useNavigate } from 'react';
import { CheckCircle, Loader2, Calendar, Menu, FileText, Plus } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { EmptyState, LoadingState, ErrorState } from '../../../components/ui/States';
import '../../student/components/courses.css';

export function CourseCreatePage() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset
  } = useForm();

  const onSubmit = async (data) => {
    setSaving(true);
    setError('');
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
      const response = await coursesApi.create(payload);
      navigate(`/teacher/courses/${response.id}`);
    } catch (err) {
      setError('Failed to create course. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <EmptyState
        title="Course Creation (Preview Mode)"
        description="Connect to the backend API to enable course creation."
        action={() => {}}
      />
    );
  }

  return (
    <AppShell>
      <PageHeader eyebrow="Create Course" title="New Course" description="Build your next learning experience">
        <Button variant="secondary" onClick={() => navigate(-1, { replace: true })}>
          <Loader2 size={16} /> Back to Dashboard
        </Button>
      </PageHeader>
      <div className="course-create-form">
        {error && <ErrorState message={error} />}

        <form onSubmit={handleSubmit(onSubmit)} className="course-create-form-body">
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
            <textarea className="form-textarea" {...register('markdown_content')} placeholder="Write course content in Markdown..." rows={4} />
          </div>

          <div className="form-group">
            <label className="form-label">LaTeX Content</label>
            <textarea className="form-textarea" {...register('latex_content')} placeholder="Write LaTeX formulas..." rows={3} />
          </div>

          <div className="form-group">
            <label className="form-label">Scheduled Publish At</label>
            <input className="form-input" type="datetime-local" {...register('scheduled_publish_at')} />
          </div>

          <div className="form-actions">
            <Button type="submit" disabled={saving} className="btn-course-primary">
              {saving ? 'Saving…' : 'Create Course'}
            </Button>
            <Button variant="outline" onClick={() => navigate(-1, { replace: true })} disabled={saving} className="btn-course-ghost">
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
