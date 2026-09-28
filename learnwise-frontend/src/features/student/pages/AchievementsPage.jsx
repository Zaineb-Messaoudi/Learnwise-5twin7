import React from 'react';
import { ArrowRight, BookOpen, Check, Sparkles, Target, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader, ProgressBar } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { analyticsApi } from '../../../api/analytics.api';
import { isBackendApiEnabled } from '../../../api/client';

const badges = [
  { title: 'First course completed', detail: 'Finish your first course', status: 'Earned', progress: 100, icon: <BookOpen size={18} /> },
  { title: 'Quiz explorer', detail: 'Complete 5 practice quizzes', status: 'In progress', progress: 60, icon: <Target size={18} /> },
  { title: 'Learning streak', detail: 'Study 7 days in a row', status: 'Earned', progress: 100, icon: <Zap size={18} /> },
  { title: 'Curious mind', detail: 'Ask 10 course-grounded questions', status: 'In progress', progress: 40, icon: <Sparkles size={18} /> },
];

export function AchievementsPage() {
  const query = useQuery({ queryKey: ['analytics', 'achievements'], queryFn: analyticsApi.achievements, enabled: isBackendApiEnabled });
  if (isBackendApiEnabled && query.isLoading) return <AppShell><PageHeader eyebrow="Learning analytics" title="Celebrate your progress."/><LoadingState label="Loading achievements"/></AppShell>;
  if (isBackendApiEnabled && query.isError) return <AppShell><PageHeader eyebrow="Learning analytics" title="Celebrate your progress."/><ErrorState message="Achievements could not be loaded." action={<Button onClick={() => query.refetch()}>Retry</Button>}/></AppShell>;
  const results = query.data?.results || query.data || [];
  const items = isBackendApiEnabled ? results.map((item, index) => ({ ...item, title: item.title, status: item.status === 'earned' ? 'Earned' : 'In progress', icon: badges[index % badges.length].icon })) : badges;
  return <AppShell><PageHeader eyebrow={`Student workspace · ${isBackendApiEnabled ? query.data?.data_source === 'live' ? 'Live data' : 'Learning analytics' : 'Illustrative data'}`} title="Celebrate your progress." description={isBackendApiEnabled ? 'Milestones earned and the next goals available in your learning journey.' : 'An illustrative view of earned milestones and the next goals to work toward.'} action={<Link to="/student/progress" className="button button-secondary">View progress <ArrowRight size={15} /></Link>} />{items.length ? <section className="list-grid" aria-label="Learning achievements">{items.map((badge, index) => <article className="list-card" key={badge.id || badge.title}><div className={`list-card-icon ${badge.status === 'Earned' ? 'orange' : 'purple'}`}>{badge.icon || badges[index % badges.length].icon}</div><div><span className="eyebrow">{badge.status === 'Earned' ? <><Check size={12} /> EARNED</> : 'IN PROGRESS'}</span><h3>{badge.title}</h3><p>{badge.detail}</p><ProgressBar value={badge.progress} label={`${badge.title}: ${badge.progress}% complete`} /></div></article>)}</section> : <p className="state-panel">No achievements yet. Complete learning activities to earn your first milestone.</p>}</AppShell>;
}
