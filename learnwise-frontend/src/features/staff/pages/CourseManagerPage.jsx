import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, BookOpen, Check, Edit3, Plus, Save } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';
import './content-management.css';

const demoCourses = [
  { id: 'neural-networks', title: 'AI & Machine Learning', description: 'Build intuition for how modern models learn from examples.', level: 'Intermediate', language: 'en', status: 'published' },
  { id: 'design-thinking', title: 'Design Thinking Foundations', description: 'Learn to frame challenges and synthesize research.', level: 'Beginner', language: 'en', status: 'draft' },
];
const emptyCourse = { title: '', description: '', level: 'beginner', language: 'en' };

export function CourseManagerPage() {
  const location = useLocation();
  const [courses, setCourses] = useState(isBackendApiEnabled ? [] : demoCourses);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(emptyCourse);
  const [loading, setLoading] = useState(isBackendApiEnabled);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const isCreateRoute = location.pathname.endsWith('/new');
  useEffect(() => {
    if (!isBackendApiEnabled) return undefined;
    let active = true;
    coursesApi.list().then(response => { if (active) setCourses(Array.isArray(response) ? response : response.results || []); })
      .catch(() => { if (active) setError('Could not load your courses. Please try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const choose = course => {
    setSelectedId(course.id);
    setForm({ title: course.title || '', description: course.description || '', level: course.level || 'beginner', language: course.language || 'en' });
    setError('');
    setNotice('');
  };
  const startNew = () => {
    setSelectedId(null);
    setForm(emptyCourse);
    setError('');
    setNotice('');
  };
  const save = async event => {
    event.preventDefault();
    if (!form.title.trim() || !form.description.trim()) {
      setError('Add a course title and description before saving.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const payload = { ...form, title: form.title.trim(), description: form.description.trim() };
      if (isBackendApiEnabled) {
        const saved = selectedId ? await coursesApi.update(selectedId, payload) : await coursesApi.create(payload);
        setCourses(current => selectedId ? current.map(course => course.id === selectedId ? saved : course) : [saved, ...current]);
        setSelectedId(saved.id);
      } else if (selectedId) {
        setCourses(current => current.map(course => course.id === selectedId ? { ...course, ...payload } : course));
      } else {
        const course = { id: `demo-course-${Date.now()}`, ...payload, status: 'draft' };
        setCourses(current => [course, ...current]);
        setSelectedId(course.id);
      }
      setNotice('Course draft updated.');
    } catch {
      setError('Could not save the course. Your edits are still here; please try again.');
    } finally { setSaving(false); }
  };
  const publish = async () => {
    if (!selectedId) {
      setError('Save this course before publishing.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      if (isBackendApiEnabled) await coursesApi.publish(selectedId);
      setCourses(current => current.map(course => course.id === selectedId ? { ...course, status: 'published' } : course));
      setNotice('Course updated.');
    } catch {
      setError('The course could not be published. Check its required fields and retry.');
    } finally { setSaving(false); }
  };
  return <AppShell role="teacher"><PageHeader eyebrow="Content management · Teacher workspace" title="Courses with a clear path." description="Create the course container, then attach materials and review their processing before you publish." action={<Button onClick={startNew}><Plus size={15}/> New course</Button>} />
    <div className="course-manager-layout">
      <section className="course-manager-list" aria-label="Course library">
        {loading ? <p className="content-state" role="status">Loading courses…</p> : courses.map(course => <button type="button" key={course.id} className={`course-manager-item ${selectedId === course.id ? 'selected' : ''}`} onClick={() => choose(course)}><span><BookOpen size={17}/></span><span><b>{course.title}</b><small>{course.status || 'draft'} · {course.level || 'Level not set'}</small></span><ArrowRight size={15}/></button>)}
        {!loading && !courses.length && <p className="content-state">Create a course to start adding learning materials.</p>}
      </section>
      <form className="course-manager-form" onSubmit={save}>
        <header><div><span className="eyebrow">{selectedId ? 'COURSE DETAILS' : 'NEW COURSE DRAFT'}</span><h2>{selectedId ? 'Edit course' : 'Create a course'}</h2></div>{selectedId && <span className={`content-status ${courses.find(course => course.id === selectedId)?.status || 'draft'}`}>{courses.find(course => course.id === selectedId)?.status || 'draft'}</span>}</header>
        <label>Course title<input name="title" value={form.title} onChange={event => setForm(current => ({ ...current, title: event.target.value }))} placeholder="e.g. Foundations of machine learning…" required /></label>
        <label>Description<textarea name="description" rows={4} value={form.description} onChange={event => setForm(current => ({ ...current, description: event.target.value }))} placeholder="What will learners understand or be able to do?" required /></label>
        <div className="assessment-fields"><label>Level<select value={form.level} onChange={event => setForm(current => ({ ...current, level: event.target.value }))}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><label>Language<select value={form.language} onChange={event => setForm(current => ({ ...current, language: event.target.value }))}><option value="en">English</option><option value="fr">French</option><option value="ar">Arabic</option></select></label></div>
        {error && <p className="assessment-error" role="alert"><AlertCircle size={15}/>{error}</p>}
        {notice && <p className="assessment-notice" role="status"><Check size={15}/>{notice}</p>}
        <div className="course-manager-actions"><Button type="submit" disabled={saving}><Save size={15}/>{saving ? 'Saving…' : 'Save draft'}</Button>{selectedId && <Button type="button" variant="secondary" disabled={saving} onClick={() => void publish()}>Publish course</Button>}</div>
        {selectedId && <Link to="/teacher/materials" className="course-material-next"><Edit3 size={14}/> Manage course materials <ArrowRight size={14}/></Link>}
        {isCreateRoute && !selectedId && <p className="course-create-hint">A course stays a draft until you explicitly publish it.</p>}
      </form>
    </div>
  </AppShell>;
}
