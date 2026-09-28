import React from 'react';
import { ArrowRight, Target, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader, ProgressBar, StatCard } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { analyticsApi } from '../../../api/analytics.api';
import { isBackendApiEnabled } from '../../../api/client';

const topics = [
  { name: 'Activation functions', score: 92, trend: 'Strong topic' },
  { name: 'Backpropagation', score: 76, trend: 'Building confidence' },
  { name: 'Validation & generalization', score: 58, trend: 'Worth another review' },
];

export function PerformancePage() {
  const query = useQuery({ queryKey: ['analytics', 'performance', '30d'], queryFn: () => analyticsApi.performance('30d'), enabled: isBackendApiEnabled });
  if (isBackendApiEnabled && query.isLoading) return <AppShell><PageHeader eyebrow="Learning analytics" title="Understand your performance."/><LoadingState label="Loading assessment signals"/></AppShell>;
  if (isBackendApiEnabled && query.isError) return <AppShell><PageHeader eyebrow="Learning analytics" title="Understand your performance."/><ErrorState message="Performance data could not be loaded." action={<Button onClick={() => query.refetch()}>Retry</Button>}/></AppShell>;
  const data = query.data || {};
  const shownTopics = isBackendApiEnabled ? data.topics || [] : topics;
  return <AppShell><PageHeader eyebrow={`Student workspace · ${isBackendApiEnabled ? data.data_source === 'live' ? 'Live data' : 'Learning analytics' : 'Illustrative data'}`} title="Understand your performance." description={isBackendApiEnabled ? 'See how completed assessments translate into topic-level strengths and useful review suggestions.' : 'Example topic-level signals to help choose what to review next.'} action={<Link to="/student/quizzes" className="button button-secondary">Practice a quiz <ArrowRight size={15} /></Link>} /><div className="stats-grid four"><StatCard icon={<Target size={19} />} label="Average quiz score" value={`${data.average_score ?? (isBackendApiEnabled ? 0 : 82)}%`} trend={isBackendApiEnabled ? 'Completed attempts' : 'Illustrative result'} tone="purple" /><StatCard icon={<TrendingUp size={19} />} label="Strong topics" value={String(data.strong_topics ?? (isBackendApiEnabled ? 0 : 1)).padStart(2, '0')} trend={isBackendApiEnabled ? 'Topics above 80%' : 'Example topics'} tone="green" /></div><section className="section-block"><div className="section-title"><div><span className="eyebrow">TOPIC CHECK-IN</span><h2>Where to focus</h2></div></div>{shownTopics.length ? <div className="focus-list">{shownTopics.map(topic => <div key={topic.name}><span className="focus-icon purple"><Target size={16} /></span><div><b>{topic.name}</b><span>{topic.trend}</span></div><ProgressBar value={topic.score} label={`${topic.name}: ${topic.score}%`} /><strong>{topic.score}%</strong></div>)}</div> : <p className="state-panel">Complete a quiz or exercise to see topic-level learning signals here.</p>}</section>{!isBackendApiEnabled && <p className="quiz-helper">Illustrative scores do not represent real learner assessment data.</p>}</AppShell>;
}
