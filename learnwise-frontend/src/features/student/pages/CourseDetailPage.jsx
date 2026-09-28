import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, CirclePlay, Play } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader, ProgressBar } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { coursesApi } from '../../../api/courses.api';
import { materialsApi } from '../../../api/materials.api';
import { analyticsApi } from '../../../api/analytics.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoCourse = {
  id: 'ai-101',
  title: 'Neural networks basics',
  description: 'Build intuition for how modern models learn from examples.',
  level: 'Intermediate',
  materials_count: 8,
  progress: 68,
};
const demoMaterials = [
  { id: 'chapter-1', title: 'Foundations', status: 'completed', kind: 'document' },
  { id: 'chapter-4', title: 'Backpropagation', status: 'processing', kind: 'audio' },
];

function recordsFrom(response) {
  return Array.isArray(response) ? response : response?.results || [];
}

export function CourseDetailPage({ player = false }) {
  const { id = 'ai-101' } = useParams();
  const [session, setSession] = useState(null);
  const [selectedMaterial, setSelectedMaterial] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const courseQuery = useQuery({
    queryKey: ['content', 'course', id],
    queryFn: () => coursesApi.detail(id),
    enabled: isBackendApiEnabled,
  });
  const materialsQuery = useQuery({
    queryKey: ['content', 'materials', id],
    queryFn: () => materialsApi.list(id),
    enabled: isBackendApiEnabled,
  });
  const course = isBackendApiEnabled ? courseQuery.data : demoCourse;
  const materials = isBackendApiEnabled ? recordsFrom(materialsQuery.data) : demoMaterials;
  const selected = materials.find(material => material.id === selectedMaterial) || materials.find(material => material.status === 'completed') || materials[0];
  const progress = Number(course?.progress?.percentage ?? course?.progress?.completion_percentage ?? course?.progress ?? (isBackendApiEnabled ? 0 : 68));

  if (isBackendApiEnabled && (courseQuery.isLoading || materialsQuery.isLoading)) return <AppShell><PageHeader eyebrow="Course workspace" title="Loading course"/><LoadingState label="Loading course content"/></AppShell>;
  if (isBackendApiEnabled && (courseQuery.isError || materialsQuery.isError || !course)) return <AppShell><PageHeader eyebrow="Course workspace" title="This course could not be opened."/><ErrorState message="Course details or materials are unavailable." action={<Button onClick={() => { void courseQuery.refetch(); void materialsQuery.refetch(); }}>Retry</Button>}/></AppShell>;

  const beginLearning = async () => {
    if (!isBackendApiEnabled) return;
    setBusy(true);
    setError('');
    try {
      const nextSession = await analyticsApi.startLearningSession(id);
      setSession(nextSession);
      await analyticsApi.recordActivity({ session_id: nextSession.id, course_id: id, activity_type: 'lesson_started', material_id: selected?.id });
    } catch {
      setError('Could not start or track this learning session. Retry before continuing.');
    } finally {
      setBusy(false);
    }
  };
  const finishLearning = async () => {
    if (!session?.id) return;
    setBusy(true);
    setError('');
    try {
      await analyticsApi.recordActivity({ session_id: session.id, course_id: id, activity_type: 'lesson_completed', material_id: selected?.id });
      await analyticsApi.finishLearningSession(session.id);
      setSession(null);
    } catch {
      setError('Could not finish this learning session. Your progress event may still be pending; retry to close it.');
    } finally {
      setBusy(false);
    }
  };

  return <AppShell><PageHeader eyebrow="Course workspace" title={course.title || 'Course'} description={course.description || 'Build knowledge through course materials and practice.'} action={<Link className="button" to={player ? `/student/courses/${id}` : `/student/courses/${id}/player`}>{player ? <><ArrowLeft size={15}/> Course overview</> : <><Play size={15}/> Continue lesson</>}</Link>}/><section className="chart-card detail-table"><span className="eyebrow">{course.level || 'Course'} · {materials.length} materials</span><h2>{player ? selected?.title || 'Your next lesson' : 'A guided path through the fundamentals'}</h2><p className="quiz-helper">{player ? 'Follow the lesson, pause when you need to, and check your understanding before moving on.' : 'Review course materials, then continue with the next available lesson.'}</p><ProgressBar value={progress}/>{error && <p className="upload-error" role="alert">{error}</p>}{player ? <><div className="transcript">{materials.map(material => <button type="button" key={material.id} className="course-material-next" onClick={() => setSelectedMaterial(material.id)}><span><strong>{material.title || material.file_name}</strong><small>{material.kind} · {material.status}</small></span>{selected?.id === material.id ? <CirclePlay size={16}/> : <ArrowRight size={16}/>}</button>)}</div>{isBackendApiEnabled && <div className="course-manager-actions">{session ? <Button onClick={() => void finishLearning()} disabled={busy}><Check size={15}/>{busy ? 'Saving…' : 'Complete session'}</Button> : <Button onClick={() => void beginLearning()} disabled={busy || !selected}><CirclePlay size={15}/>{busy ? 'Starting…' : 'Start learning session'}</Button>}{session && <span role="status">Learning session active · progress events are being tracked</span>}</div>}{!isBackendApiEnabled && <div className="transcript"><p><strong>01:12</strong> A prediction is compared with the expected result.</p><p><strong>03:48</strong> The error travels backward through the network.</p><p><strong>06:42</strong> Each weight receives a small corrective update.</p></div>}</> : <div className="list-grid">{materials.slice(0, 3).map((material, index) => <article className="list-card" key={material.id}><div className="list-card-icon purple"><Check size={18}/></div><div><span className="eyebrow">{material.status || (index ? 'UP NEXT' : 'MATERIAL')}</span><h3>{material.title || material.file_name}</h3><p>{material.kind === 'audio' ? 'Listen to the course recording.' : 'Review this course source.'}</p></div></article>)}</div>}{!materials.length && <p className="state-panel">No course materials have been published yet.</p>}</section></AppShell>;
}
