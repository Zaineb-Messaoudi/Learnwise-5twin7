import React from 'react';
import { ArrowRight, BookOpen, Check, Clock3, Compass, MessageCircle, Target } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import '../../../pages/signature-pages.css';
import { AppShell } from '../../../layouts/AppShell';
import { useAuth } from '../../../contexts/AuthContext';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { analyticsApi } from '../../../api/analytics.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoMove = {
  course_title: 'AI & Machine Learning',
  current_topic: 'Neural networks',
  next_topic: 'Backpropagation',
  action: '3-question practice',
  estimated_minutes: 18,
  difficulty: 'Medium stretch',
};

export function AtlasDashboardPage() {
  const { user } = useAuth();
  const overviewQuery = useQuery({ queryKey: ['analytics', 'student-overview', '30d'], queryFn: () => analyticsApi.studentOverview('30d'), enabled: isBackendApiEnabled });
  const dateLabel = new Intl.DateTimeFormat(navigator.language, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const firstName = user?.name?.split(' ')[0] || 'there';
  if (isBackendApiEnabled && overviewQuery.isLoading) return <AppShell><div className="atlas-dashboard"><div className="dashboard-heading"><div><p className="atlas-kicker">{dateLabel}</p><h1>{greeting}, {firstName}.</h1></div></div><LoadingState label="Loading your learning overview"/></div></AppShell>;
  if (isBackendApiEnabled && overviewQuery.isError) return <AppShell><div className="atlas-dashboard"><PageHeader eyebrow="Learning analytics" title={`${greeting}, ${firstName}.`}/><ErrorState message="Your learning overview could not be loaded." action={<Button onClick={() => overviewQuery.refetch()}>Retry</Button>}/></div></AppShell>;
  const overview = overviewQuery.data || {};
  const move = isBackendApiEnabled ? overview.next_best_move : demoMove;
  const activity = isBackendApiEnabled ? overview.weekly_activity || [] : [{ label: 'Mon', value: 38 }, { label: 'Tue', value: 58 }, { label: 'Wed', value: 46 }, { label: 'Thu', value: 72 }, { label: 'Fri', value: 55 }, { label: 'Sat', value: 86 }, { label: 'Sun', value: 68 }];
  const steps = overview.path_steps?.length
    ? overview.path_steps.map((step, index) => ({ ...step, label: step.label || ['YOUR CHAPTER', 'CONNECT THIS IDEA', 'THEN TRY'][index] || 'NEXT STEP', state: step.state === 'current' ? 'current' : step.state === 'completed' ? 'current' : index === 1 ? 'focus' : 'next' }))
    : move ? [
      { label: 'YOUR CHAPTER', title: move.current_topic, state: 'current' },
      { label: 'CONNECT THIS IDEA', title: move.next_topic, state: 'focus' },
      { label: 'THEN TRY', title: move.action, state: 'next' },
    ] : [];
  const progress = overview.stats || {};
  return <AppShell><div className="atlas-dashboard">
    <div className="dashboard-heading"><div><p className="atlas-kicker">{dateLabel}</p><h1>{greeting}, {firstName}.</h1><p className="dashboard-subtitle">{isBackendApiEnabled ? 'Your learning activity and next steps, in one place.' : 'The map is open. Here is the most useful place to begin.'}</p></div><Link to="/student/learning-path" className="atlas-button atlas-button-bright">Open full atlas <Compass size={16} aria-hidden="true"/></Link></div>
    {move ? <section className="dashboard-command" aria-labelledby="next-move-heading">
      <div className="command-copy"><p className="atlas-kicker">Your next best move</p><h2 id="next-move-heading">Connect the dots<br/><i>in {move.course_title || 'your course'}.</i></h2><p>Continue from {move.current_topic || 'your current topic'} to {move.next_topic || 'the next concept'} with a focused learning activity.</p><div className="command-source"><BookOpen size={15} aria-hidden="true"/><span>{move.course_title || 'Your course'}</span>{move.chapter && <b>{move.chapter}</b>}</div><div className="command-meta"><span><Clock3 size={14} aria-hidden="true"/> {move.estimated_minutes || 15} min</span><span><Target size={14} aria-hidden="true"/> {move.difficulty || 'Recommended'}</span></div><Link to={move.href || '/student/exercises'} className="atlas-button atlas-button-dark">{move.cta || 'Continue the thread'} <ArrowRight size={15} aria-hidden="true"/></Link></div>
      <figure className="command-map" aria-labelledby="command-map-caption"><figcaption id="command-map-caption" className="command-map-caption"><span>YOUR LEARNING PATH</span><b>{steps.length} connected steps</b></figcaption><svg className="command-map-connections" viewBox="0 0 1000 560" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="learning-path-gradient" x1="0" x2="1"><stop offset="0%" stopColor="#d8ff45"/><stop offset="52%" stopColor="#57d8ff"/><stop offset="100%" stopColor="#ff4f87"/></linearGradient></defs><path className="command-map-path-glow" d="M170 390 C300 390 300 205 470 205 S690 390 830 390"/><path className="command-map-path" d="M170 390 C300 390 300 205 470 205 S690 390 830 390"/><path className="command-map-path-mobile command-map-path-glow" d="M500 90 C500 190 500 190 500 280 S500 370 500 470"/></svg>{steps.map((step, index) => <div key={`${step.state}-${step.title}`} className={`command-map-step map-step-${step.state}`} aria-current={step.state === 'focus' ? 'step' : undefined}><span className="map-step-marker">{step.state === 'current' ? <Check size={13} aria-hidden="true"/> : step.state === 'focus' ? <span/> : <Target size={13} aria-hidden="true"/>}</span><span className="map-step-copy"><small>{step.label}</small><b>{step.title}</b></span></div>)}<div className="command-map-footer"><span><i/> {isBackendApiEnabled ? 'Recommended from your progress' : 'Suggested learning thread'}</span><span>1 of {steps.length}</span></div></figure>
    </section> : <section className="dashboard-empty"><BookOpen size={24}/><div><h2>Your next step will appear here</h2><p>Enroll in a course and complete a learning activity to build your personalized map.</p></div><Link className="button button-secondary" to="/student/courses">Explore courses <ArrowRight size={14}/></Link></section>}
    <div className="dashboard-lower"><section className="signal-panel"><div className="panel-head"><div><p className="atlas-kicker">The signal</p><h2>Your learning rhythm</h2></div><span className="signal-score">{isBackendApiEnabled ? progress.streak_days ?? 0 : 7} <small>day streak</small></span></div>{activity.length ? <div className="rhythm-bars" aria-label="Learning activity for the selected period">{activity.slice(-7).map((item, index) => <span key={item.label || index} title={`${item.label}: ${item.hours ?? item.value} hours`} style={{ height: `${Math.min(item.value ?? (item.hours || 0) / 3 * 100, 100)}%` }}/>)}</div> : <p className="state-panel">Your activity rhythm will appear after your first learning session.</p>}</section><section className="companion-panel"><MessageCircle size={20} aria-hidden="true"/><p className="atlas-kicker">Your companion</p><h2>One question can<br/><i>change the map.</i></h2><Link to="/student/assistant" className="atlas-text-action">Ask a better question <ArrowRight size={15} aria-hidden="true"/></Link></section></div>
  </div></AppShell>;
}
