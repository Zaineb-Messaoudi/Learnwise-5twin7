import React from 'react';
import { Activity, BookOpen, MessageCircle, Target, Users } from 'lucide-react';
import { StatCard } from '../../../components/shared/Primitives';

export function MetricGrid({ admin = false, data, backend = false }) {
  const stats = data?.stats || {};
  const metrics = admin
    ? [[<Users size={19}/>, 'Total users', stats.user_count, 'Across Learnwise', 'purple'], [<BookOpen size={19}/>, 'Active courses', stats.course_count, 'Published courses', 'blue'], [<MessageCircle size={19}/>, 'AI interactions', stats.assistant_interactions, 'Assistant sessions', 'green'], [<Activity size={19}/>, 'Active today', stats.active_users_today, 'Today', 'orange']]
    : [[<BookOpen size={19}/>, 'Total courses', stats.course_count, 'Your courses', 'purple'], [<Users size={19}/>, 'Active students', stats.enrolled_students, 'Enrolled learners', 'blue'], [<Target size={19}/>, 'Avg. performance', stats.average_quiz_score == null ? null : `${stats.average_quiz_score}%`, 'Completed assessments', 'green'], [<Activity size={19}/>, 'Quiz completion', stats.quiz_completion_rate == null ? null : `${stats.quiz_completion_rate}%`, 'Attempt completion', 'orange']];
  const demo = admin
    ? [['12,842', '+14.8%'], ['346', '+21 this month'], ['84.2k', '+24.6%'], ['2,491', '+8.4%']]
    : [['08', '+2 this month'], ['1,248', '+12.4%'], ['84%', '+4.2%'], ['72%', '+8.1%']];
  return <div className="stats-grid four">{metrics.map(([icon, label, value, trend, tone], index) => <StatCard key={label} icon={icon} label={label} value={backend ? value ?? '—' : demo[index][0]} trend={backend ? value == null ? 'No data yet' : trend : demo[index][1]} tone={tone}/>)}</div>;
}
