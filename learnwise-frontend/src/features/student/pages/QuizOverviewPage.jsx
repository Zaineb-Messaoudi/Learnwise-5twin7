import React from 'react';
import { ArrowRight, Check, Clock3, ListChecks, BookOpen } from 'lucide-react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader, ProgressBar } from '../../../components/shared/Primitives';
import { EmptyState, ErrorState, LoadingState } from '../../../components/ui/States';
import { quizzesApi } from '../../../api/quizzes.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoQuiz = { id: 'demo', title: 'Neural Networks Check-in', description: 'A short source-grounded practice set from your Chapter 4 notebook.', questions: Array.from({ length: 4 }) };

export function QuizOverviewPage() {
  const { id = 'demo' } = useParams();
  const [searchParams] = useSearchParams();
  const chapterId = searchParams.get('chapter') || undefined;
  const quizQuery = useQuery({
    queryKey: ['assessment', 'quiz', id],
    queryFn: () => quizzesApi.detail(id),
    enabled: isBackendApiEnabled,
  });
  if (isBackendApiEnabled && quizQuery.isLoading) return <AppShell><PageHeader eyebrow="Quiz workspace" title="Loading quiz"/><LoadingState label="Loading assessment details"/></AppShell>;
  if (isBackendApiEnabled && (quizQuery.isError || !quizQuery.data)) return <AppShell><PageHeader eyebrow="Quiz workspace" title="This quiz could not be opened."/><ErrorState message="Quiz details are unavailable." action={<Button onClick={() => void quizQuery.refetch()}>Retry</Button>}/></AppShell>;
  const quiz = isBackendApiEnabled ? quizQuery.data : demoQuiz;
  const questionCount = quiz.questions?.length || 0;
  const duration = quiz.estimated_minutes || Math.max(questionCount * 2, 1);
  const isChapterQuiz = Boolean(quiz.chapter_id);
  return (
    <AppShell>
      <PageHeader
        eyebrow="Quiz workspace"
        title={quiz.title || 'Practice quiz'}
        description={quiz.description || 'A focused check of the ideas in your course.'}
        action={<Link className="button" to={`/student/quizzes/${id}/attempt`}>Start quiz <ArrowRight size={15} /></Link>}
      />
      <section className="chart-card detail-table">
        <div className="list-card-icon purple"><ListChecks size={20} /></div>
        <h2>Test the ideas that matter</h2>
        <p className="quiz-helper">{quiz.description || 'Move through the questions, review your answers, and get feedback when you submit.'}</p>
        <div className="command-meta"><span><Clock3 size={14} /> {duration} minutes</span><span><Check size={14} /> {questionCount} questions</span>{isChapterQuiz && <span><BookOpen size={14} /> Chapitre {quiz.chapter_id}</span>}</div>
        <ProgressBar value={0} />
        <Link className="button button-secondary" to={`/student/quizzes/${id}/attempt`}>Begin practice <ArrowRight size={15} /></Link>
        {isChapterQuiz && chapterId && (
          <Link className="button button-secondary" to={`/student/courses/${quiz.course_id}?chapter=${chapterId}`} style={{ marginTop: 8 }}>Back to chapter <ArrowRight size={15} /></Link>
        )}
      </section>
    </AppShell>
  );
}
