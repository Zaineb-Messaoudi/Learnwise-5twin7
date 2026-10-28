import React, { useMemo } from 'react';
import { ArrowRight, RotateCcw, Trophy } from 'lucide-react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ScoreCard } from '../../../components/quizzes/ScoreCard';
import { quizzesApi } from '../../../api/quizzes.api';
import { isBackendApiEnabled } from '../../../api/client';
import { ErrorState, LoadingState } from '../../../components/ui/States';

export function QuizResultPage() {
  const { state } = useLocation();
  const { id = 'demo' } = useParams();
  const [searchParams] = useSearchParams();
  const attemptId = state?.attemptId || searchParams.get('attempt') || (() => {
    try { return window.sessionStorage.getItem(`learnwise:quiz-attempt:${id}`); } catch { return null; }
  })();
  const evaluationQuery = useQuery({
    queryKey: ['assessment', 'evaluation', id, attemptId],
    queryFn: () => quizzesApi.result(id, attemptId),
    enabled: isBackendApiEnabled && Boolean(attemptId) && !state?.evaluation,
  });
  const result = useMemo(() => {
    if (state && Number.isFinite(state.score) && Number.isFinite(state.total) && state.total > 0) return state;
    const evaluation = state?.evaluation || evaluationQuery.data?.evaluation || evaluationQuery.data;
    if (evaluation) {
      const score = Number(evaluation.correct_answers ?? evaluation.score);
      const total = Number(evaluation.total_questions ?? evaluation.total);
      if (Number.isFinite(score) && Number.isFinite(total) && total > 0) return { score, total, evaluation, badge: evaluation.badge };
    }
    try {
      const saved = JSON.parse(window.sessionStorage.getItem(`learnwise:quiz-result:${id}`) || 'null');
      return saved && Number.isFinite(saved.score) && Number.isFinite(saved.total) && saved.total > 0 ? saved : null;
    } catch { return null; }
  }, [id, state, evaluationQuery.data]);
  if (isBackendApiEnabled && attemptId && evaluationQuery.isLoading && !state?.evaluation) return <AppShell><PageHeader eyebrow="Quiz result" title="Loading your evaluation"/><LoadingState label="Loading assessment feedback"/></AppShell>;
  if (isBackendApiEnabled && evaluationQuery.isError && !state?.evaluation) return <AppShell><PageHeader eyebrow="Quiz result" title="Your evaluation could not be loaded."/><ErrorState message="Your attempt was submitted, but feedback is unavailable right now." action={<Button onClick={() => void evaluationQuery.refetch()}>Retry</Button>}/></AppShell>;
  if (!result) return <AppShell><PageHeader eyebrow="Quiz result" title="No completed attempt found." description="Finish a practice attempt first. Its score will appear here." action={<Link className="button" to={`/student/quizzes/${id}`}><ArrowRight size={15} /> Open quiz overview</Link>} /></AppShell>;
  const total = result.total;
  const correct = result.score;
  const incorrect = Math.max(0, total - correct);
  const badge = result.badge;
  return (
    <AppShell>
      <PageHeader eyebrow="Quiz result" title={correct >= total / 2 ? 'A strong foundation.' : 'A useful first signal.'} description="This score reflects your submitted answers. Unanswered questions count as incorrect." action={<Link className="button" to={`/student/quizzes/${id}/attempt`}><RotateCcw size={15} /> Try again</Link>} />
      <div className="detail-table">
        <ScoreCard score={Math.round(correct / total * 100)} correct={correct} incorrect={incorrect} />
        <section className="chart-card">
          <h2>Suggested next step</h2>
          <p className="quiz-helper">Revisit activation functions, then try the short exercise on gradient descent.</p>
          {result.evaluation?.feedback && <p>{result.evaluation.feedback}</p>}
          <Link className="button button-secondary" to="/student/exercises/demo">Open exercise <ArrowRight size={15} /></Link>
        </section>
        {badge && (
          <section className="chart-card">
            <div className="badge-card">
              <Trophy size={48} />
              <h2>Badge gagné !</h2>
              <p>{badge.name}</p>
              <p>{badge.description}</p>
              <small>Obtenu le {badge.awarded_at ? new Date(badge.awarded_at).toLocaleDateString() : '—'}</small>
            </div>
          </section>
        )}
      </div>
      {result.evaluation?.question_feedback?.length > 0 && (
        <section className="section-block">
          <div className="section-title"><h2>Question feedback</h2></div>
          <div className="list-grid">
            {result.evaluation.question_feedback.map((item, index) => (
              <article className="list-card" key={item.question_id || index}>
                <div>
                  <span className="eyebrow">{item.is_correct ? 'CORRECT' : 'REVIEW'}</span>
                  <h3>{item.question || `Question ${index + 1}`}</h3>
                  <p>{item.feedback}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </AppShell>
  );
}
