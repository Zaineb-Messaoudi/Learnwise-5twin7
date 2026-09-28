import React from 'react';
import { ArrowRight, ListChecks } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { EmptyState, ErrorState, LoadingState } from '../../../components/ui/States';
import { quizzesApi } from '../../../api/quizzes.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoQuizzes = [{ id: 'demo', title: 'Neural Networks Check-in', description: 'Activation functions, backpropagation, loss, and validation.', difficulty: 'Intermediate', question_count: 4 }];
function resultsFrom(response) { return Array.isArray(response) ? response : response?.results || []; }

export function QuizLibraryPage() {
  const query = useQuery({ queryKey: ['assessment', 'quizzes'], queryFn: () => quizzesApi.list(), enabled: isBackendApiEnabled });
  if (isBackendApiEnabled && query.isLoading) return <AppShell><PageHeader eyebrow="Assessment" title="Practice quizzes"/><LoadingState label="Loading published quizzes"/></AppShell>;
  if (isBackendApiEnabled && query.isError) return <AppShell><PageHeader eyebrow="Assessment" title="Practice quizzes"/><ErrorState message="Quizzes could not be loaded." action={<Button onClick={() => void query.refetch()}>Retry</Button>}/></AppShell>;
  const quizzes = isBackendApiEnabled ? resultsFrom(query.data) : demoQuizzes;
  return <AppShell><PageHeader eyebrow="Assessment" title="Practice quizzes" description="Check your understanding and get feedback tied to your course learning."/><section className="list-grid">{quizzes.map(quiz => <article className="list-card" key={quiz.id}><div className="list-card-icon purple"><ListChecks size={18}/></div><div><span className="eyebrow">{quiz.difficulty || 'PRACTICE'} · {quiz.question_count ?? quiz.questions?.length ?? 0} QUESTIONS</span><h3>{quiz.title}</h3><p>{quiz.description || quiz.course_title || 'Course assessment'}</p><Link to={`/student/quizzes/${quiz.id}`} className="atlas-text-action">View quiz <ArrowRight size={14}/></Link></div></article>)}</section>{!quizzes.length && <EmptyState title="No published quizzes yet. Explore a course or check back later." action={<Link className="button button-secondary" to="/student/courses">Explore courses</Link>}/>}</AppShell>;
}
