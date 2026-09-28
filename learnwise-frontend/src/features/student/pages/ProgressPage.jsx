import React from 'react';
import { Clock3, Sparkles, Target, Trophy, Zap } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { PageHeader, ProgressBar, StatCard } from '../../../components/shared/Primitives';
import { Button } from '../../../components/shared/Primitives';
import { LoadingState, ErrorState } from '../../../components/ui/States';
import { analyticsApi } from '../../../api/analytics.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoActivity = [{ label: 'Mon', hours: 1.2 }, { label: 'Tue', hours: 1.8 }, { label: 'Wed', hours: 1.4 }, { label: 'Thu', hours: 2.1 }, { label: 'Fri', hours: 1.6 }, { label: 'Sat', hours: 2.4 }, { label: 'Sun', hours: 1.9 }];
const demoFocusAreas = [{ name: 'Probability & statistics', score: 38, trend: 'Needs more practice' }, { name: 'Research synthesis', score: 74, trend: 'Looking good' }];
export function ProgressPage() {
  const query = useQuery({ queryKey: ['analytics', 'student-overview', '30d'], queryFn: () => analyticsApi.studentOverview('30d'), enabled: isBackendApiEnabled });
  if (isBackendApiEnabled && query.isLoading) return <AppShell><PageHeader eyebrow="Learning analytics" title="See how far you’ve come."/><LoadingState label="Loading your learning progress"/></AppShell>;
  if (isBackendApiEnabled && query.isError) return <AppShell><PageHeader eyebrow="Learning analytics" title="See how far you’ve come."/><ErrorState message="Progress could not be loaded." action={<Button onClick={() => query.refetch()}>Retry</Button>}/></AppShell>;
  const overview = query.data || {};
  const stats = overview.stats || {};
  const activity = isBackendApiEnabled ? overview.weekly_activity || [] : demoActivity;
  const focusAreas = isBackendApiEnabled ? overview.focus_areas || [] : demoFocusAreas;
  const learningHours = stats.learning_hours ?? (isBackendApiEnabled ? 0 : 12.4);
  const quizScore = stats.average_quiz_score ?? (isBackendApiEnabled ? 0 : 87);
  const streak = stats.streak_days ?? (isBackendApiEnabled ? 0 : 7);
  const achievementCount = stats.achievement_count ?? (isBackendApiEnabled ? 0 : 8);
  const isLive = isBackendApiEnabled && overview.data_source === 'live';
  return <AppShell><PageHeader eyebrow={`Student workspace · ${isBackendApiEnabled ? isLive ? 'Live data' : 'Learning analytics' : 'Illustrative data'}`} title="See how far you’ve come." description={isBackendApiEnabled ? 'Learning hours, assessment results, activity, and topics to revisit from your account.' : 'Illustrative learning activity and focus areas. Connect a learner account to see real progress.'} /><div className="stats-grid four"><StatCard icon={<Clock3 size={19} />} label="Learning hours" value={Number(learningHours).toFixed(1)} trend={isBackendApiEnabled ? 'Selected range' : 'Illustrative week'} tone="purple" /><StatCard icon={<Target size={19} />} label="Avg. quiz score" value={`${quizScore}%`} trend={isBackendApiEnabled ? 'Completed attempts' : 'Illustrative result'} tone="green" /><StatCard icon={<Zap size={19} />} label="Day streak" value={String(streak).padStart(2, '0')} trend={isBackendApiEnabled ? 'Consecutive study days' : 'Illustrative streak'} tone="orange" /><StatCard icon={<Trophy size={19} />} label="Achievements" value={String(achievementCount).padStart(2, '0')} trend={isBackendApiEnabled ? 'Earned milestones' : 'Illustrative count'} tone="blue" /></div><section className="chart-card"><div className="chart-head"><div><span className="eyebrow">{isBackendApiEnabled ? 'LEARNING SESSIONS · HOURS PER DAY' : 'ILLUSTRATIVE ACTIVITY · HOURS PER DAY'}</span><h2>Your weekly rhythm</h2></div><span className="chart-legend"><i /> Hours learned</span></div>{activity.length ? <><div className="rhythm-bars" role="img" aria-label={activity.map(item => `${item.label}: ${item.hours} hours`).join(', ')}>{activity.map(item => <span key={item.label} title={`${item.label}: ${item.hours} hours`} style={{ height: `${Math.min(Number(item.hours) / 3 * 100, 100)}%` }} />)}</div><div className="chart-labels">{activity.map(item => <span key={item.label}>{item.label}<b>{item.hours}h</b></span>)}</div></> : <p className="state-panel">No learning sessions in this date range yet. Start a lesson or practice set to build your rhythm.</p>}</section><section className="section-block"><div className="section-title"><div><span className="eyebrow">{isBackendApiEnabled ? 'PERSONALIZED SIGNALS' : 'ILLUSTRATIVE FOCUS AREAS'}</span><h2>Topics to revisit</h2></div></div>{focusAreas.length ? <div className="focus-list">{focusAreas.map((item, index) => <div key={item.name}><span className={`focus-icon ${index ? 'purple' : 'orange'}`}>{index ? <Sparkles size={16} /> : <Target size={16} />}</span><div><b>{item.name}</b><span>{item.trend}</span></div><ProgressBar value={item.score} color={!index ? '#f1a26f' : undefined} /><strong>{item.score}%</strong></div>)}</div> : <p className="state-panel">Complete a few learning activities and your next review topics will appear here.</p>}</section></AppShell>;
}
