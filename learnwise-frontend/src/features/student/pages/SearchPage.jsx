import React, { useMemo, useState } from 'react';
import { ArrowRight, BookOpen, FileText, Search as SearchIcon, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { courses } from '../../../data/mockData';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoResults = [...courses.map(course => ({ type: 'Course', title: course.title, detail: `${course.lessons} lessons · ${course.progress}% complete`, icon: <BookOpen size={18}/>, to: `/student/courses/${course.id}` })), { type: 'Notebook', title: 'Neural Networks Lab', detail: '4 sources · updated 12 min ago', icon: <FileText size={18}/>, to: '/student/notebooks/neural-networks' }, { type: 'Assistant', title: 'Ask about backpropagation', detail: 'Open a grounded conversation', icon: <Sparkles size={18}/>, to: '/student/assistant' }];
function itemsFrom(response) { return Array.isArray(response) ? response : response?.results || []; }

export function SearchPage() {
  const [query, setQuery] = useState('');
  const courseQuery = useQuery({ queryKey: ['content', 'course-catalog'], queryFn: coursesApi.catalog, enabled: isBackendApiEnabled });
  const results = isBackendApiEnabled
    ? itemsFrom(courseQuery.data).map(course => ({ type: 'Course', title: course.title, detail: `${course.level || 'Course'} · ${course.language || 'Published'}`, icon: <BookOpen size={18}/>, to: `/student/courses/${course.id}` }))
    : demoResults;
  const shown = useMemo(() => results.filter(item => `${item.title} ${item.detail}`.toLowerCase().includes(query.toLowerCase())), [results, query]);
  if (isBackendApiEnabled && courseQuery.isLoading) return <AppShell><PageHeader eyebrow="Workspace search" title="Find your next thread."/><LoadingState label="Searching published courses"/></AppShell>;
  if (isBackendApiEnabled && courseQuery.isError) return <AppShell><PageHeader eyebrow="Workspace search" title="Search is unavailable."/><ErrorState message="Published courses could not be loaded." action={<Button onClick={() => void courseQuery.refetch()}>Retry</Button>}/></AppShell>;
  return <AppShell><PageHeader eyebrow="Workspace search" title="Find your next thread." description={isBackendApiEnabled ? 'Search published courses available to you.' : 'Search sample courses, notebooks, and learning spaces.'}/><label className="global-search"><SearchIcon size={18}/><span className="sr-only">Search Learnwise</span><input autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder={isBackendApiEnabled ? 'Search published courses…' : 'Search courses, notebooks, and ideas...'}/></label><div className="search-results" aria-live="polite">{shown.map(item => <Link className="search-result" to={item.to} key={`${item.type}-${item.title}`}><span className="search-result-icon">{item.icon}</span><span><small>{item.type}</small><b>{item.title}</b><em>{item.detail}</em></span><ArrowRight size={16}/></Link>)}{!shown.length && <p className="empty-search">No matching learning spaces yet.</p>}</div></AppShell>;
}
