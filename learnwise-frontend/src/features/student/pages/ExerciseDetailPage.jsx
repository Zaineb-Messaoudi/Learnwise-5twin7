import React, { useMemo, useState } from 'react';
import { AlertCircle, ArrowLeft, Check, Target } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { exercisesApi } from '../../../api/exercises.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoExercise = {
  id: 'demo',
  title: 'Build a simple classifier',
  prompt: 'A classifier separates examples into meaningful groups. Which choice describes the role of a decision boundary?',
  choices: [
    { id: 'boundary', text: 'A line or surface that separates classes' },
    { id: 'examples', text: 'A list of every training example' },
    { id: 'speed', text: 'A score that only measures speed' },
  ],
};

export function ExerciseDetailPage() {
  const { id = 'demo' } = useParams();
  const [answer, setAnswer] = useState('');
  const [evaluation, setEvaluation] = useState(null);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const exerciseQuery = useQuery({
    queryKey: ['assessment', 'exercise', id],
    queryFn: () => exercisesApi.detail(id),
    enabled: isBackendApiEnabled,
  });
  const exercise = isBackendApiEnabled ? exerciseQuery.data : demoExercise;
  const choices = useMemo(() => (exercise?.choices || exercise?.options || []).map((choice, index) => typeof choice === 'string' ? { id: String(index), text: choice } : ({ ...choice, text: choice.text || choice.label || choice.title })), [exercise]);
  if (isBackendApiEnabled && exerciseQuery.isLoading) return <AppShell><PageHeader eyebrow="Practice exercise" title="Loading exercise"/><LoadingState label="Loading assessment"/></AppShell>;
  if (isBackendApiEnabled && (exerciseQuery.isError || !exercise)) return <AppShell><PageHeader eyebrow="Practice exercise" title="This exercise could not be opened."/><ErrorState message="Assessment details are unavailable." action={<Button onClick={() => void exerciseQuery.refetch()}>Retry</Button>}/></AppShell>;
  const submit = async () => {
    if (!answer) {
      setError('Choose an answer before submitting.');
      return;
    }
    setError('');
    if (!isBackendApiEnabled) {
      setEvaluation({ is_correct: answer === 'boundary', feedback: answer === 'boundary' ? 'Correct. The boundary separates examples by their predicted class.' : 'Review how classifiers divide examples into predicted groups.' });
      return;
    }
    setSubmitting(true);
    try {
      const response = await exercisesApi.submit(id, answer);
      setEvaluation(response.evaluation || response);
    } catch (cause) {
      setError(cause?.response?.data?.detail || 'Your response could not be submitted. Try again.');
    } finally {
      setSubmitting(false);
    }
  };
  return <AppShell><PageHeader eyebrow="Practice exercise" title={exercise.title || 'Practice exercise'} description={exercise.description || 'Apply the concept and receive helpful feedback.'} action={<Link className="button button-secondary" to="/student/exercises"><ArrowLeft size={15}/> Back to exercises</Link>}/><section className="chart-card detail-table"><div className="list-card-icon orange"><Target size={20}/></div><h2>{exercise.question_title || 'Apply what you learned'}</h2><p className="quiz-helper">{exercise.prompt || exercise.question}</p><div className="answer-options">{choices.map(choice => <label className={answer === choice.id ? 'selected' : ''} key={choice.id}><input type="radio" name="exercise-answer" value={choice.id} checked={answer === choice.id} onChange={() => { setAnswer(choice.id); setEvaluation(null); setError(''); }}/><span>{choice.text}</span></label>)}</div>{error && <p className="upload-error" role="alert"><AlertCircle size={15}/>{error}</p>}{evaluation ? <p role="status" className={evaluation.is_correct ? 'success-message' : 'quiz-helper'}><Check size={15}/>{evaluation.feedback || (evaluation.is_correct ? 'Correct. Nice work.' : 'Review the explanation and try another practice.')}</p> : <Button onClick={() => void submit()} disabled={submitting}>{submitting ? 'Checking…' : 'Submit answer'}</Button>}</section></AppShell>;
}
