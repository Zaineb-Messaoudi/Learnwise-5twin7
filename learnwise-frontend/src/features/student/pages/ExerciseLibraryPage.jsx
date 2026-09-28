import React from 'react';
import { ArrowRight, Target } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { EmptyState, ErrorState, LoadingState } from '../../../components/ui/States';
import { exercisesApi } from '../../../api/exercises.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoExercises = [{ id: 'demo', title: 'Build a simple classifier', description: 'Apply the concept and receive helpful feedback.', difficulty: 'Foundational' }];
function resultsFrom(response) { return Array.isArray(response) ? response : response?.results || []; }

export function ExerciseLibraryPage() {
  const query = useQuery({ queryKey: ['assessment', 'exercises'], queryFn: () => exercisesApi.list(), enabled: isBackendApiEnabled });
  if (isBackendApiEnabled && query.isLoading) return <AppShell><PageHeader eyebrow="Assessment" title="Practice exercises"/><LoadingState label="Loading published exercises"/></AppShell>;
  if (isBackendApiEnabled && query.isError) return <AppShell><PageHeader eyebrow="Assessment" title="Practice exercises"/><ErrorState message="Exercises could not be loaded." action={<Button onClick={() => void query.refetch()}>Retry</Button>}/></AppShell>;
  const exercises = isBackendApiEnabled ? resultsFrom(query.data) : demoExercises;
  return <AppShell><PageHeader eyebrow="Assessment" title="Practice exercises" description="Apply what you learn with short, feedback-rich practice."/><section className="list-grid">{exercises.map(exercise => <article className="list-card" key={exercise.id}><div className="list-card-icon orange"><Target size={18}/></div><div><span className="eyebrow">{exercise.difficulty || 'PRACTICE'}</span><h3>{exercise.title}</h3><p>{exercise.description || exercise.prompt || 'Apply this concept and receive feedback.'}</p><Link to={`/student/exercises/${exercise.id}`} className="atlas-text-action">Open exercise <ArrowRight size={14}/></Link></div></article>)}</section>{!exercises.length && <EmptyState title="No published exercises yet. Explore a course or check back later." action={<Link className="button button-secondary" to="/student/courses">Explore courses</Link>}/>}</AppShell>;
}
