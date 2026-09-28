import React from 'react';
import { Clock3, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { PageHeader, Button } from '../../../components/shared/Primitives';
import { MetricGrid } from '../components/MetricGrid';
import { StaffActivity } from '../components/StaffActivity';
import { LoadingState, ErrorState } from '../../../components/ui/States';
import { analyticsApi } from '../../../api/analytics.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoActivity = [{ label: 'Mon', value: 45 }, { label: 'Tue', value: 62 }, { label: 'Wed', value: 52 }, { label: 'Thu', value: 78 }, { label: 'Fri', value: 66 }, { label: 'Sat', value: 88 }];

function WorkspaceDashboard({ role }) {
  const admin = role === 'admin';
  const query = useQuery({
    queryKey: ['analytics', `${role}-overview`, '30d'],
    queryFn: () => admin ? analyticsApi.adminOverview('30d') : analyticsApi.teacherOverview('30d'),
    enabled: isBackendApiEnabled,
  });
  if (isBackendApiEnabled && query.isLoading) return <AppShell role={role}><PageHeader eyebrow={`${admin ? 'Admin' : 'Instructor'} workspace`} title="Loading your overview"/><LoadingState label="Loading workspace analytics"/></AppShell>;
  if (isBackendApiEnabled && query.isError) return <AppShell role={role}><PageHeader eyebrow={`${admin ? 'Admin' : 'Instructor'} workspace`} title="Workspace overview unavailable"/><ErrorState message="Analytics could not be loaded." action={<Button onClick={() => void query.refetch()}>Retry</Button>}/></AppShell>;
  const overview = query.data || {};
  const activity = isBackendApiEnabled ? overview.weekly_activity || [] : demoActivity;
  const heading = admin ? 'Platform overview' : 'Good morning, Maya.';
  const chartTitle = admin ? 'Platform activity' : 'Learner activity';
  return <AppShell role={role}>
    <PageHeader eyebrow={`${admin ? 'Admin' : 'Instructor'} workspace · ${isBackendApiEnabled ? overview.data_source === 'live' ? 'Live data' : 'Analytics' : 'Illustrative data'}`} title={heading} description={admin ? 'A pulse check across Learnwise.' : 'Here’s how your learners are doing this week.'} action={admin ? null : <Link className="button" to="/teacher/courses/new"><Plus size={16}/> Create course</Link>}/>
    <MetricGrid admin={admin} data={overview} backend={isBackendApiEnabled}/>
    <section className="charts-grid"><div className="chart-card wide"><span className="eyebrow">{admin ? 'PLATFORM GROWTH' : 'LEARNER ACTIVITY'}</span><h2>{chartTitle}</h2>{activity.length ? <div className="rhythm-bars" aria-label={`${chartTitle} for the selected period`}>{activity.map((item, index) => <span key={item.label || index} title={`${item.label || ''}: ${item.value ?? item.hours ?? 0}`} style={{ height: `${Math.min(Number(item.value ?? item.hours ?? 0), 100)}%` }}/>)}</div> : <p className="state-panel">No activity has been recorded for this period yet.</p>}</div><div className="chart-card"><span className="eyebrow">SIGNAL</span><h2>{isBackendApiEnabled ? 'Selected period' : 'Illustrative overview'}</h2><p className="quiz-helper">{isBackendApiEnabled ? 'Metrics reflect activity within the selected date range.' : 'These sample figures illustrate how workspace analytics will appear.'}</p>{!isBackendApiEnabled && <strong className="signal-score">+18.4%</strong>}</div></section>
    <StaffActivity teacher={!admin} activity={overview.recent_activity} backend={isBackendApiEnabled}/>
  </AppShell>;
}
export function TeacherDashboard() { return <WorkspaceDashboard role="teacher"/>; }
export function AdminDashboard() { return <WorkspaceDashboard role="admin"/>; }
export function TeacherAnalyticsPage() { return <WorkspaceDashboard role="teacher"/>; }
export function AdminAnalyticsPage() { return <WorkspaceDashboard role="admin"/>; }
