import React, { useState, useParams } from 'react';
import { CheckCircle, Loader2, Calendar, FileText } from 'lucide-react';
import { coursesApi } from '../../../api/courses.api';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import '../../student/components/courses.css';

export function CourseSchedulePage() {
  const { id } = useParams();
  const [scheduled, setScheduled] = useState(null);
  const [status, setStatus] = useState('draft');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const statusColors = {
    published: { bg: '#f4f7ff', border: '#dbe4ff', color: '#17205c' },
    draft: { bg: '#fff0e4', border: '#ffe4c2', color: '#3a2a10' },
    archived: { bg: '#e3f5ef', border: '#bee5ee', color: '#2a5a72' },
  };

  // Fetch course
  React.useEffect(() => {
    if (!id) return;
    coursesApi.detail(id).then((course) => {
      setScheduled(course.scheduled_publish_at);
      setStatus(course.status);
    });
  }, [id]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await coursesApi.update(id, { scheduled_publish_at: scheduled });
      setStatus('published');
      setSaving(false);
    } catch (err) {
      setError('Failed to update schedule. Please try again.');
      setSaving(false);
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <AppShell>
        <PageHeader eyebrow="Scheduled Publishing" title="Schedule Publishing" description="Set course publish date" />
        <ErrorState message="API disabled - connect to backend." />
      </AppShell>
    );
  }

  if (!id) {
    return (
      <AppShell>
        <PageHeader eyebrow="Scheduled Publishing" title="Schedule Publishing" description="Course not found." />
      </AppShell>
    );
  }

  const statusStyle = statusColors[status] || statusColors.draft;

  return (
    <AppShell>
      <PageHeader eyebrow="Scheduled Publishing" title="Schedule Publishing" description="Set when this course will auto-publish" />
      {error && <ErrorState message={error} />}
      <div className="course-schedule">
        <form className="schedule-form" onSubmit={onSubmit}>
          <div className="form-group">
            <label className="form-label">Current Status</label>
            <span className={`status-badge ${status}`}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">Scheduled Publish At</label>
            <input
              className="form-input"
              type="datetime-local"
              value={scheduled ? new Date(scheduled).toISOString().slice(0, 16) : ''}
              onChange={(e) => setScheduled(e.target.value)}
              disabled={saving}
            />
          </div>

          {scheduled && (
            <p className="schedule-note">
              If the scheduled time is in the past, the course will auto-publish on next save.
            </p>
          )}

          <div className="form-actions">
            <Button type="submit" disabled={saving} className="btn-course-primary">
              {saving ? 'Saving…' : scheduled ? 'Update Schedule' : 'Set Schedule'}
            </Button>
            <Button variant="outline" onClick={() => window.history.back()} className="btn-course-ghost">
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
