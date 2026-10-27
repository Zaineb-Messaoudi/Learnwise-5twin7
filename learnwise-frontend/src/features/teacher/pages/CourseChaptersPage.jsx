import React, { useState, useRef, useEffect } from 'react';
import { CheckCircle, Loader2, FileText, Menu, ArrowUpDown, Trash, Edit } from 'lucide-react';
import { coursesApi } from '../../../api/courses.api';
import { materialsApi } from '../../../api/materials.api';
import { AppShell } from '../../../layouts/AppShell';
import { Button, ProgressBar } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState, EmptyState } from '../../../components/ui/States';
import '../../student/components/courses.css';

export function CourseChaptersPage({ courseId }) {
  const [chapters, setChapters] = useState([]);
  const [newChapterTitle, setNewChapterTitle] = useState('');
  const [editingChapter, setEditingChapter] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const chapterListRef = useRef(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  // Fetch chapters
  React.useEffect(() => {
    if (!courseId) return;
    coursesApi.detail(courseId).then((course) => {
      setChapters(course.chapters || []);
    });
  }, [courseId]);

  // Create chapter
  const onCreate = async (data) => {
    setSaving(true);
    setError('');
    try {
      const chapter = await materialsApi.createChapter({
        course: courseId,
        title: data.title,
        description: data.description,
        order: chapters.length,
      });
      setChapters(prev => [...prev, chapter]);
      setNewChapterTitle('');
    } catch (err) {
      setError('Failed to create chapter. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Update chapter
  const onUpdate = async (chapterId, data) => {
    setSaving(true);
    setError('');
    try {
      await materialsApi.updateChapter(chapterId, data);
      setChapters(prev =>
        prev.map((c) => (c.id === chapterId ? { ...c, title: data.title, description: data.description } : c))
      );
      setEditingChapter(null);
    } catch (err) {
      setError('Failed to update chapter. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Delete chapter
  const onDelete = async (chapterId) => {
    if (!window.confirm('Are you sure you want to delete this chapter?')) return;
    setSaving(true);
    setError('');
    try {
      await materialsApi.deleteChapter(chapterId);
      setChapters(prev => prev.filter((c) => c.id !== chapterId));
    } catch (err) {
      setError('Failed to delete chapter. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <EmptyState
        title="Chapter Management (Preview Mode)"
        description="Connect to the backend API to enable chapter management."
        action={() => {}}
      />
    );
  }

  return (
    <AppShell>
      <PageHeader eyebrow="Course Chapters" title="Course Chapters" description="Organize your course content into chapters" />
      {error && <ErrorState message={error} />}
      <div className="chapter-management">
        <div className="chapter-form">
          <h3 className="section-title">{editingChapter ? 'Edit Chapter' : 'Add Chapter'}</h3>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (editingChapter) {
                onUpdate(editingChapter, { title: editingTitle });
              } else {
                onCreate({ title: newChapterTitle, description: '' });
              }
            }}
          >
            <input
              className="chapter-input"
              placeholder="Chapter title"
              {...register('title', { required: true })}
              defaultValue={newChapterTitle}
              onChange={(e) => setNewChapterTitle(e.target.value)}
            />
            <Button type="submit" disabled={saving} className="btn-course-primary">
              {saving ? 'Saving…' : editingChapter ? 'Update' : 'Add Chapter'}
            </Button>
          </form>
        </div>

        <h3 className="section-title">Existing Chapters</h3>
        {chapters.length === 0 && <p className="empty-text">No chapters yet. Add one above.</p>}

        <div className="chapter-list">
          {chapters.map((chapter, idx) => (
            <div key={chapter.id} className="chapter-item">
              <div className="chapter-info">
                <span className="chapter-title">{chapter.title}</span>
                {chapter.description && <span className="chapter-description">{chapter.description}</span>}
              </div>
              <div className="chapter-actions">
                <Button variant="outline" size="sm" onClick={() => setEditingChapter(chapter.id)} className="chapter-btn-edit">
                  <Edit size={12} /> Edit
                </Button>
                <Button variant="danger" size="sm" onClick={() => onDelete(chapter.id)} className="chapter-btn-delete">
                  <Trash size={12} /> Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
