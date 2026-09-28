import React from 'react';
import { ArrowLeft, Check, LockKeyhole, Target } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import '../../../pages/signature-pages.css';
import { AppShell } from '../../../layouts/AppShell';
import { analyticsApi } from '../../../api/analytics.api';
import { isBackendApiEnabled } from '../../../api/client';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';

const demoPoints = [{ id: 'foundations', title: 'Foundations', meta: 'Completed / 6 concepts', state: 'done' }, { id: 'neural-networks', title: 'Neural networks', meta: 'In motion / 4 concepts', state: 'current', href: '/student/courses/ai-101' }, { id: 'responsible-ai', title: 'Responsible AI', meta: 'Next / 3 concepts', state: 'next' }, { id: 'synthesis', title: 'Your synthesis', meta: 'Locked / unlocks at 80%', state: 'locked' }];
export function LearningPathPage() {
  const listQuery = useQuery({ queryKey: ['analytics', 'learning-paths'], queryFn: analyticsApi.learningPaths, enabled: isBackendApiEnabled });
  const paths = listQuery.data?.results || listQuery.data || [];
  const pathId = paths[0]?.id;
  const detailQuery = useQuery({ queryKey: ['analytics', 'learning-path', pathId], queryFn: () => analyticsApi.learningPath(pathId), enabled: isBackendApiEnabled && Boolean(pathId) });
  if (isBackendApiEnabled && listQuery.isLoading) return <AppShell><PageHeader eyebrow="Learning analytics" title="Your learning path"/><LoadingState label="Loading your connected path"/></AppShell>;
  if (isBackendApiEnabled && (listQuery.isError || detailQuery.isError)) return <AppShell><PageHeader eyebrow="Learning analytics" title="Your learning path"/><ErrorState message="Your learning path could not be loaded." action={<Button onClick={() => { void listQuery.refetch(); if (pathId) void detailQuery.refetch(); }}>Retry</Button>}/></AppShell>;
  const path = detailQuery.data || {};
  const points = isBackendApiEnabled ? path.nodes || [] : demoPoints;
  const getState = item => item.state === 'completed' ? 'done' : item.state === 'locked' ? 'locked' : item.state === 'current' || item.state === 'in_progress' ? 'current' : 'next';
  return <AppShell><div className="path-page"><Link className="atlas-text-action" to="/student/dashboard"><ArrowLeft size={16}/> Back to overview</Link><div className="dashboard-heading"><div><p className="atlas-kicker">{isBackendApiEnabled ? 'Your personalized path' : 'Your connected path'}</p><h1>{path.title || 'Learning is not a line.'}</h1><p className="dashboard-subtitle">{path.description || 'It is a set of ideas that start speaking to each other.'}</p></div><span className="path-progress"><Check size={15}/> {path.connected_concepts ?? (isBackendApiEnabled ? 0 : 12)} concepts connected</span></div>{points.length ? <div className="path-canvas" aria-label="Learning path">{points.map((point, index) => {
    const state = getState(point);
    const position = { left: `${12 + index * (76 / Math.max(points.length - 1, 1))}%`, top: `${18 + (index % 2) * 32}%` };
    const content = <><span className="path-point-ring"><span>{state === 'locked' ? <LockKeyhole size={13}/> : state === 'done' ? <Check size={13}/> : state === 'current' ? <Target size={13}/> : index + 1}</span></span><div><h2>{point.title}</h2><p>{point.meta || point.description || ''}</p></div></>;
    return point.href && state !== 'locked'
      ? <Link className={`path-point ${state}`} style={position} key={point.id || point.title} to={point.href}>{content}</Link>
      : <article className={`path-point ${state}`} style={position} key={point.id || point.title} aria-current={state === 'current' ? 'step' : undefined}>{content}</article>;
  })}</div> : <div className="state-panel">Your learning path will appear after you enroll in a course and begin learning.</div>}</div></AppShell>;
}
