import React, { useState, useEffect } from 'react';
import { CheckCircle, Loader2, FileText, Calendar, Trash, Edit } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { isBackendApiEnabled } from '../../../api/client';
import { coursesApi } from '../../../api/courses.api';
import { AppShell } from '../../../layouts/AppShell';
import { Button, ProgressBar, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState, EmptyState } from '../../../components/ui/States';
import '../../student/components/courses.css';

export function CourseVersionsPage({ courseId }) {
  const [versions, setVersions] = useState([]);
  const [newVersionDescription, setNewVersionDescription] = useState('');
  const [editingVersion, setEditingVersion] = useState(null);
  const [deleteVersionId, setDeleteVersionId] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  // Fetch versions
  React.useEffect(() => {
    if (!courseId) return;
    coursesApi.versions(courseId).then((data) => {
      setVersions(data || []);
    });
  }, [courseId]);

  // Create version
  const onCreate = async (description) => {
    setSaving(true);
    setError('');
    try {
      const version = await coursesApi.createVersion(courseId, { change_description: description });
      setVersions(prev => [version, ...prev]);
      setNewVersionDescription('');
    } catch (err) {
      setError('Failed to create version. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Rollback version
  const onRollback = async (versionId) => {
    if (!window.confirm('Are you sure you want to rollback to this version?')) return;
    setSaving(true);
    setError('');
    try {
      await coursesApi.rollback(courseId, versionId);
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      setError('Failed to rollback. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <EmptyState
        title="Course Versioning (Preview Mode)"
        description="Connect to the backend API to enable versioning."
        action={() => {}}
      />
    );
  }

  return (
    <AppShell>
      <PageHeader eyebrow="Course Versioning" title="Course Versions" description="Track course snapshots and rollback" />
      {error && <ErrorState message={error} />}
      <div className="version-management">
        <div className="version-form">
          <h3 className="section-title">Create New Version</h3>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onCreate(newVersionDescription);
            }}
          >
            <input
              className="version-input"
              placeholder="Change description"
              {...register('description', { required: true })}
              defaultValue={newVersionDescription}
              onChange={(e) => setNewVersionDescription(e.target.value)}
            />
            <Button type="submit" disabled={saving} className="btn-course-primary">
              {saving ? 'Saving…' : 'Create Version'}
            </Button>
          </form>
        </div>

        <div className="version-list">
          <h3 className="section-title">Version History</h3>
          {versions.length === 0 && <p className="empty-text">No versions yet. Create your first version above.</p>}
          <div className="version-items">
            {versions.map((version, idx) => (
              <div key={version.id} className="version-item">
                <div className="version-info">
                  <span className="version-number">v{version.version_number}</span>
                  <span className="version-description">{version.change_description || 'No description'}</span>
                </div>
                <div className="version-actions">
                  <Button variant="danger" size="sm" onClick={() => setDeleteVersionId(version.id)} className="version-btn-delete">
                    Delete
                  </Button>
                  {editingVersion === version.id && (
                    <>
                      <input
                        className="version-edit-input"
                        placeholder="New description"
                        onChange={(e) => setEditingVersion({ ...editingVersion, change_description: e.target.value })}
                      />
                      <Button type="button" onClick={() => {}} className="version-btn-save">
                        Save
                      </Button>
                    </>
                  )}
                  <Button variant="danger" size="sm" style={{ marginLeft: '8px' }} onClick={() => onRollback(version.id)} className="version-btn-rollback">
                    Rollback
                  </Button>
                </div>
              </div>
            ))}
          </div>
          {deleteVersionId && (
            <p className="confirm-text">Are you sure you want to delete version {deleteVersionId}?</p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
