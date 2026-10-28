import React from 'react';
import { ArrowRight, Clock3, Sparkles, Target, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader, ProgressBar, StatCard } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { analyticsApi } from '../../../api/analytics.api';
import { isBackendApiEnabled } from '../../../api/client';

export function PerformancePage() {
  const performance = useQuery({ queryKey: ['analytics', 'performance', '30d'], queryFn: () => analyticsApi.performance('30d'), enabled: isBackendApiEnabled });
  const weakness = useQuery({ queryKey: ['analytics', 'weaknesses'], queryFn: () => analyticsApi.weaknesses(2), enabled: isBackendApiEnabled });
  const recommendations = useQuery({ queryKey: ['analytics', 'recommendations'], queryFn: analyticsApi.recommendations, enabled: isBackendApiEnabled });
  const radar = useQuery({ queryKey: ['analytics', 'radar'], queryFn: analyticsApi.radar, enabled: isBackendApiEnabled });
  const queries = [performance, weakness, recommendations, radar];
  const loading = isBackendApiEnabled && queries.some(query => query.isLoading);
  const failed = isBackendApiEnabled && queries.some(query => query.isError);

  if (loading) return <AppShell><PageHeader eyebrow="Learning analytics" title="Understand your performance."/><LoadingState label="Loading assessment signals"/></AppShell>;
  if (failed) return <AppShell><PageHeader eyebrow="Learning analytics" title="Understand your performance."/><ErrorState message="Performance data could not be loaded." action={<Button onClick={() => queries.forEach(query => query.refetch())}>Retry</Button>}/></AppShell>;

  const data = performance.data || {};
  const topics = data.topics || [];
  const weaknesses = weakness.data?.concepts || [];
  const radarActions = (radar.data?.risks || []).flatMap(risk =>
    (risk.interventions || []).filter(item => !item.completed_at).map(item => ({
      ...item,
      course: risk.course,
      riskLevel: risk.risk_level,
      href: item.type === 'take_quiz' ? '/student/quizzes' : '/student/courses',
    })),
  );
  const ruleActions = (recommendations.data || []).map(item => ({
    ...item,
    course: item.course_title,
    riskLevel: item.priority,
    estimated_minutes: null,
    href: item.type === 'weak_score' ? '/student/quizzes' : '/student/courses',
  }));
  const recommendedActions = [...radarActions, ...ruleActions]
    .filter((item, index, items) => items.findIndex(candidate => candidate.title === item.title) === index)
    .slice(0, 3);

  return <AppShell>
    <PageHeader eyebrow={`Student workspace · ${isBackendApiEnabled ? 'Live data' : 'Illustrative data'}`} title="Understand your performance." description="Every signal is tied to recorded assessments and mapped concepts." action={<Link to="/student/quizzes" className="button button-secondary">Practice a quiz <ArrowRight size={15}/></Link>}/>
    <div className="stats-grid four"><StatCard icon={<Target size={19}/>} label="Average quiz score" value={data.assessment_count ? `${data.average_score}%` : '—'} trend={`${data.assessment_count ?? 0} completed attempt${data.assessment_count === 1 ? '' : 's'}`} tone="purple"/><StatCard icon={<TrendingUp size={19}/>} label="Strong topics" value={String(data.strong_topics ?? 0).padStart(2, '0')} trend="Topics above 80%" tone="green"/></div>
    <section className="section-block"><div className="section-title"><div><span className="eyebrow">COURSE PERFORMANCE</span><h2>Recorded results</h2></div></div>{topics.length ? <div className="focus-list">{topics.map(topic => <div key={topic.name}><span className="focus-icon purple"><Target size={16}/></span><div><b>{topic.name}</b><span>{topic.trend}</span></div><ProgressBar value={topic.score}/><strong>{topic.score}%</strong></div>)}</div> : <p className="state-panel">No completed assessment result is available yet.</p>}</section>
    {isBackendApiEnabled && <section className="section-block"><div className="section-title"><div><span className="eyebrow">EVIDENCE-BASED WEAK POINTS</span><h2>Errors by mapped concept</h2></div></div>{weaknesses.length ? <div className="focus-list">{weaknesses.map(item => <div key={item.concept_id}><span className="focus-icon orange"><Target size={16}/></span><div><b>{item.concept}</b><span>{item.answers} mapped answers · weighted error rate</span></div><ProgressBar value={item.error_rate}/><strong>{item.error_rate}%</strong></div>)}</div> : <p className="state-panel">{weakness.data?.reason || 'No mapped answer evidence is available yet.'}</p>}</section>}
    {isBackendApiEnabled && <section className="section-block recommendation-section"><div className="section-title"><div><span className="eyebrow">LEARNING RADAR</span><h2>Recommended for you</h2></div><span className="recommendation-live"><i/> Based on live activity</span></div>{recommendedActions.length ? <div className="recommendation-grid">{recommendedActions.map((item, index) => <article className="recommendation-card" key={`${item.title}-${index}`}><span className="recommendation-icon"><Sparkles size={18}/></span><div className="recommendation-copy"><small>{item.course || `${item.riskLevel || 'Personalized'} priority`}</small><h3>{item.title}</h3><p>{item.reason}</p>{item.estimated_minutes && <span className="recommendation-time"><Clock3 size={13}/> About {item.estimated_minutes} min</span>}</div><Link to={item.href} className="button button-secondary">Start <ArrowRight size={14}/></Link></article>)}</div> : <div className="recommendation-clear"><Sparkles size={21}/><div><h3>No urgent recommendation</h3><p>Your recorded activity does not currently show a learning risk. Complete more sessions and assessments to keep the Radar updated.</p></div></div>}</section>}
  </AppShell>;
}
