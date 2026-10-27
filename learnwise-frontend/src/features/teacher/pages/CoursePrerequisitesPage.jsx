import React, { useState, useEffect } from 'react';
import { CheckCircle, Loader2, FileText, Plus, Trash, Search } from 'lucide-react';
import { coursesApi } from '../../../api/courses.api';
import { AppShell } from '../../../layouts/AppShell';
import { Button, ProgressBar } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState, EmptyState } from '../../../components/ui/States';
import '../../student/components/courses.css';

export function CoursePrerequisitesPage({ courseId }) {
  const [prerequisites, setPrerequisites] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  // Fetch prerequisites
  React.useEffect(() => {
    if (!courseId) return;
    coursesApi.prerequisites(courseId).then((data) => {
      setPrerequisites(data || []);
    });
  }, [courseId]);

  // Add prerequisite
  const onAdd = async (selectedId) => {
    setSaving(true);
    setError('');
    try {
      await coursesApi.addPrerequisite(courseId, { prerequisite_course: selectedId });
      setPrerequisites(prev => [...prev, { id: selectedId, title: 'Loading...' }]);
    } catch (err) {
      setError('Failed to add prerequisite. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Remove prerequisite
  const onRemove = async (prereqId) => {
    if (!window.confirm('Are you sure you want to remove this prerequisite?')) return;
    setSaving(true);
    setError('');
    try {
      await coursesApi.removePrerequisite(courseId, prereqId);
      setPrerequisites(prev => prev.filter((p) => p.id !== prereqId));
    } catch (err) {
      setError('Failed to remove prerequisite. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Search courses for prerequisite
  const searchCourses = async (query) => {
    if (!query || query.length < 2) return [];
    try {
      const courses = await coursesApi.list();
      const currentCourse = await coursesApi.detail(courseId);
      const descendants = new Set(); // Would need to compute from backend

      return courses.data
        .filter(c => c.id !== courseId && !descendants.has(c.id))
        .filter(c => c.title.toLowerCase().includes(query.toLowerCase()))
        .slice(0, 5);
    } catch (err) {
      return [];
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <EmptyState
        title="Prerequisites (Preview Mode)"
        description="Connect to the backend API to enable prerequisite management."
        action={() => {}}
      />
    );
  }

  return (
    <AppShell>
      <PageHeader eyebrow="Course Prerequisites" title="Course Prerequisites" description="Set course prerequisites" />
      {error && <ErrorState message={error} />}
      <div className="prerequisite-management">
        <div className="prerequisite-form">
          <h3 className="section-title">Add Prerequisite</h3>
          <div className="prerequisite-search">
            <input
              className="prerequisite-input"
              placeholder="Search courses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Button variant="secondary" onClick={() => {} } className="prerequisite-search-btn">
              Search
            </Button>
          </div>
        </div>

        <div className="prerequisite-list">
          <h3 className="section-title">Existing Prerequisites</h3>
          {prerequisites.length === 0 && <p className="empty-text">No prerequisites set.</p>}
          <div className="prerequisite-items">
            {prerequisites.map((prereq, idx) => (
              <div key={prereq.id} className="prerequisite-item">
                <span className="prerequisite-title">{prereq.title || 'Loading...'}</span>
                <Button variant="danger" size="sm" onClick={() => onRemove(prereq.id)} className="prerequisite-btn-remove">
                  <Trash size={12} /> Remove
                </Button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
