import React, { useState, useEffect } from 'react';
import { CheckCircle, Loader2, FileText, Trash, FileSearch } from 'lucide-react';
import { coursesApi } from '../../../api/courses.api';
import { useForm } from 'react-hook-form';
import { AppShell } from '../../../layouts/AppShell';
import { Button, ProgressBar } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState, EmptyState } from '../../../components/ui/States';
import '../../student/components/courses.css';

export function CourseModerationPage() {
  const [courses, setCourses] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  // Fetch all courses
  React.useEffect(() => {
    if (!isBackendApiEnabled) return;
    coursesApi.list().then((data) => {
      setCourses(data || []);
    });
  }, [isBackendApiEnabled]);

  const statusOptions = [
    { value: 'all', label: 'All Courses' },
    { value: 'draft', label: 'Draft' },
    { value: 'pending_review', label: 'Pending Review' },
    { value: 'published', label: 'Published' },
    { value: 'archived', label: 'Archived' },
  ];

  const onStatusFilterChange = (value) => {
    setStatusFilter(value);
  };

  const submitForReview = async (courseId) => {
    setSaving(true);
    setError('');
    try {
      await coursesApi.submitForReview(courseId);
      setStatusFilter('pending_review');
    } catch (err) {
      setError('Failed to submit for review. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const approveCourse = async (courseId) => {
    setSaving(true);
    setError('');
    try {
      await coursesApi.approve(courseId);
      setCourses(prev => prev.map(c => c.id === courseId ? { ...c, status: 'published' } : c));
    } catch (err) {
      setError('Failed to approve course. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const rejectCourse = async (courseId) => {
    setSaving(true);
    setError('');
    try {
      await coursesApi.reject(courseId);
      setCourses(prev => prev.map(c => c.id === courseId ? { ...c, status: 'draft' } : c));
    } catch (err) {
      setError('Failed to reject course. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <EmptyState
        title="Admin Moderation (Preview Mode)"
        description="Connect to the backend API to enable admin moderation."
        action={() => {}}
      />
    );
  }

  const filteredCourses = statusFilter === 'all'
    ? courses
    : courses.filter(c => c.status === statusFilter);

  return (
    <AppShell>
      <PageHeader eyebrow="Admin Moderation" title="Course Moderation" description="Manage all courses" />
      <div className="moderation-toolbar">
          <select
            className="course-filters-select"
            onChange={(e) => onStatusFilterChange(e.target.value)}
            value={statusFilter}
          >
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value} selected={statusFilter === opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <Button variant="secondary" onClick={() => setStatusFilter('all')}>
            Reset
          </Button>
        </div>

        <table className="moderation-table">
          <thead>
            <tr>
              <th>Course Title</th>
              <th>Owner</th>
              <th>Status</th>
              <th>Level</th>
              <th>Language</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredCourses.slice(0, 20).map((course) => (
              <tr key={course.id}>
                <td>{course.title}</td>
                <td>{course.owner_email || 'Unknown'}</td>
                <td>
                  <span className={`status-badge ${course.status}`}>
                    {statusOptions.find(o => o.value === course.status)?.label || course.status}
                  </span>
                </td>
                <td>{course.level || '-'}</td>
                <td>{course.language || '-'}</td>
                <td>{course.created_at ? new Date(course.created_at).toLocaleDateString() : '-'}</td>
                <td>
                  <div className="moderation-actions">
                    {course.status === 'draft' && (
                      <Button variant="secondary" onClick={() => submitForReview(course.id)}>
                        Submit for Review
                      </Button>
                    )}
                    {course.status === 'pending_review' && (
                      <>
                        <Button variant="primary" onClick={() => approveCourse(course.id)}>
                          Approve
                        </Button>
                        <Button variant="danger" onClick={() => rejectCourse(course.id)}>
                          Reject
                        </Button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredCourses.length > 20 && <p className="moderation-note">Showing 20 of {filteredCourses.length} courses</p>}
      </AppShell>
    );
}
