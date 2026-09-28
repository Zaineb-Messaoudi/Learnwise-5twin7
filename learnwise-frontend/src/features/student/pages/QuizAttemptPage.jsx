import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader, ProgressBar } from '../../../components/shared/Primitives';
import { QuizQuestion } from '../../../components/quizzes/QuizQuestion';
import { QuizNavigator } from '../../../components/quizzes/QuizNavigator';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { quizzesApi } from '../../../api/quizzes.api';
import { isBackendApiEnabled } from '../../../api/client';
import { ErrorState, LoadingState } from '../../../components/ui/States';

const demoQuestions = [
  { id: 'q1', question: 'What is the primary purpose of an activation function?', options: ['To add non-linearity to the network', 'To store the training dataset', 'To remove all hidden layers', 'To measure the final score'], answer: 'To add non-linearity to the network' },
  { id: 'q2', question: 'What does backpropagation update?', options: ['The model weights', 'The file name', 'The quiz timer', 'The number of classes'], answer: 'The model weights' },
  { id: 'q3', question: 'What does a lower loss generally indicate?', options: ['A closer prediction', 'A larger dataset', 'A faster microphone', 'A longer lecture'], answer: 'A closer prediction' },
  { id: 'q4', question: 'Why keep a validation set?', options: ['To check generalization', 'To hide the labels', 'To increase font size', 'To remove the test set'], answer: 'To check generalization' },
];

function responseData(response) {
  return response?.attempt || response?.data || response;
}

function normalizeQuestion(question, index) {
  const options = question.choices || question.options || [];
  return {
    id: question.id || `question-${index}`,
    question: question.text || question.prompt || question.question || '',
    options: options.map(option => typeof option === 'string' ? option : ({ value: option.id, label: option.text || option.label || option.title })),
  };
}

export function QuizAttemptPage() {
  const navigate = useNavigate();
  const { id = 'demo' } = useParams();
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState({});
  const [dialog, setDialog] = useState(null);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const saveTimer = useRef(null);
  const quizQuery = useQuery({
    queryKey: ['assessment', 'quiz', id],
    queryFn: () => quizzesApi.detail(id),
    enabled: isBackendApiEnabled,
  });
  const attemptQuery = useQuery({
    queryKey: ['assessment', 'attempt', id],
    queryFn: async () => responseData(await quizzesApi.startAttempt(id)),
    enabled: isBackendApiEnabled && Boolean(quizQuery.data),
    staleTime: Infinity,
  });
  const attempt = attemptQuery.data;
  const questions = useMemo(() => isBackendApiEnabled
    ? (quizQuery.data?.questions || []).map(normalizeQuestion)
    : demoQuestions, [quizQuery.data]);
  const item = questions[current];
  const answered = Object.keys(answers).length;
  const score = useMemo(() => demoQuestions.reduce((total, question, index) => total + (answers[index] === question.answer ? 1 : 0), 0), [answers]);

  useEffect(() => {
    if (attempt?.answers) setAnswers(attempt.answers);
  }, [attempt?.id]);
  useEffect(() => {
    if (!isBackendApiEnabled || !attempt?.id || !Object.keys(answers).length) return undefined;
    window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      setSaving(true);
      try {
        await quizzesApi.saveAttempt(id, attempt.id, answers);
        setError('');
      } catch {
        setError('Your answer could not be saved. Keep this page open and retry before submitting.');
      } finally {
        setSaving(false);
      }
    }, 500);
    return () => window.clearTimeout(saveTimer.current);
  }, [answers, attempt?.id, id]);

  const select = answer => setAnswers(previous => ({ ...previous, [isBackendApiEnabled ? item.id : current]: answer }));
  const changeQuestion = next => {
    setCurrent(next);
  };
  const submit = async () => {
    if (isBackendApiEnabled) {
      if (!attempt?.id) {
        setError('Your quiz attempt is not ready. Retry after the quiz has loaded.');
        return;
      }
      window.clearTimeout(saveTimer.current);
      setSubmitting(true);
      setError('');
      try {
        await quizzesApi.saveAttempt(id, attempt.id, answers);
        const response = await quizzesApi.submit(id, attempt.id, answers);
        const evaluation = response?.evaluation || response;
        const total = Number(evaluation.total_questions ?? evaluation.total ?? questions.length);
        const resultScore = Number(evaluation.correct_answers ?? evaluation.score);
        if (!Number.isFinite(total) || !Number.isFinite(resultScore)) {
          throw new Error('The evaluation response did not include a score and question count.');
        }
        try { window.sessionStorage.setItem(`learnwise:quiz-attempt:${id}`, attempt.id); } catch { /* Route state still carries the evaluation. */ }
        navigate(`/student/quizzes/${id}/result`, { state: { score: resultScore, total, evaluation, attemptId: attempt.id } });
      } catch (cause) {
        setError(cause.message || 'Your quiz could not be submitted. Your answers are still available to retry.');
      } finally {
        setSubmitting(false);
      }
      return;
    }
    const result = { score, total: questions.length, answers };
    try { window.sessionStorage.setItem(`learnwise:quiz-result:${id}`, JSON.stringify(result)); }
    catch { /* The in-memory route state still carries the result for this visit. */ }
    navigate(`/student/quizzes/${id}/result`, { state: result });
  };
  const exit = () => navigate(`/student/quizzes/${id}`);
  const confirm = () => {
    const action = dialog;
    setDialog(null);
    if (action === 'submit') void submit();
    if (action === 'exit') exit();
  };

  if (isBackendApiEnabled && (quizQuery.isLoading || attemptQuery.isLoading)) {
    return <AppShell><PageHeader eyebrow="Quiz attempt" title="Loading your quiz"/><LoadingState label="Preparing your assessment attempt"/></AppShell>;
  }
  if (isBackendApiEnabled && (quizQuery.isError || attemptQuery.isError || !questions.length || !item)) {
    return <AppShell><PageHeader eyebrow="Quiz attempt" title="This quiz could not be opened."/><ErrorState message={quizQuery.error?.message || attemptQuery.error?.message || 'The quiz has no available questions.'} action={<Button onClick={() => { void quizQuery.refetch(); void attemptQuery.refetch(); }}>Retry</Button>}/></AppShell>;
  }

  return <AppShell><PageHeader eyebrow="Quiz attempt" title={isBackendApiEnabled ? quizQuery.data.title : 'Neural Networks Check-in'} description={isBackendApiEnabled ? `Your answers are ${saving ? 'being saved' : 'saved as you go'}.` : 'Your answers are kept in this browser while you move through the practice quiz.'} action={<Button variant="secondary" onClick={() => setDialog('exit')}><ArrowLeft size={15} /> Exit quiz</Button>} /><div className="quiz-layout"><section className="quiz-question"><div className="quiz-top"><span className="eyebrow">QUESTION {current + 1} OF {questions.length}</span><span>{answered} of {questions.length} answered</span></div><ProgressBar value={(current + 1) / questions.length * 100} /><QuizQuestion question={item.question} options={item.options} value={answers[isBackendApiEnabled ? item.id : current] || null} onChange={select} /><div className="quiz-actions"><Button variant="secondary" disabled={current === 0 || submitting} onClick={() => changeQuestion(Math.max(0, current - 1))}>Previous</Button>{current === questions.length - 1 ? <Button disabled={submitting || saving} onClick={() => setDialog('submit')}><Check size={15} /> {submitting ? 'Submitting…' : 'Submit quiz'}</Button> : <Button disabled={submitting} onClick={() => changeQuestion(Math.min(questions.length - 1, current + 1))}>Next question <ArrowRight size={15} /></Button>}</div>{error && <p className="assistant-inline-error" role="alert"><AlertCircle size={15}/>{error}</p>}</section><aside className="quiz-navigator"><span className="eyebrow">QUESTION NAVIGATOR</span><QuizNavigator count={questions.length} current={current} onSelect={changeQuestion} /></aside></div><ConfirmDialog open={Boolean(dialog)} title={dialog === 'exit' ? 'Leave this quiz?' : 'Submit your answers?'} message={dialog === 'exit' ? `${answered ? `${answered} answer${answered === 1 ? '' : 's'} will be discarded. ` : ''}You can start this practice again later.` : answered < questions.length ? `${questions.length - answered} question${questions.length - answered === 1 ? ' is' : 's are'} unanswered. Submit anyway? Unanswered questions count as incorrect.` : 'Your answers will be scored and this attempt will be complete.'} onClose={() => setDialog(null)} onConfirm={confirm} /></AppShell>;
}
