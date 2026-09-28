import React, { useState } from 'react';
import { BookOpen, Plus, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { createNotebook, getNotebooks } from '../data/notebookStore';
import { NotebookCard } from '../components/notebook/NotebookCard';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';
import { EmptyState, ErrorState, LoadingState } from '../../../components/ui/States';
import '../notebook.css';

export function NotebookLibraryPage() {
  const [notebooks, setNotebooks] = useState(getNotebooks);
  const [query, setQuery] = useState('');
  const coursesQuery = useQuery({ queryKey: ['content', 'course-catalog'], queryFn: coursesApi.catalog, enabled: isBackendApiEnabled });
  const create = () => setNotebooks(createNotebook());
  const shown = notebooks.filter(notebook => notebook.title.toLowerCase().includes(query.toLowerCase()));
  if (isBackendApiEnabled && coursesQuery.isLoading) return <AppShell><PageHeader eyebrow="Student workspace" title="Your course sources"/><LoadingState label="Loading published courses"/></AppShell>;
  if (isBackendApiEnabled && coursesQuery.isError) return <AppShell><PageHeader eyebrow="Student workspace" title="Your course sources"/><ErrorState message="Courses could not be loaded." action={<Button onClick={() => void coursesQuery.refetch()}>Retry</Button>}/></AppShell>;
  if (isBackendApiEnabled) {
    const availableCourses = Array.isArray(coursesQuery.data) ? coursesQuery.data : coursesQuery.data?.results || [];
    return <AppShell><PageHeader eyebrow="Student workspace" title="Your course notebooks" description="Open a course to select its materials, ask source-grounded questions, and create study resources."/><section className="list-grid">{availableCourses.map(course => <article className="list-card" key={course.id}><div className="list-card-icon purple"><BookOpen size={18}/></div><div><span className="eyebrow">{course.materials_count || 0} MATERIALS</span><h3>{course.title}</h3><p>{course.description || course.level || 'Published course'}</p><Link to={`/student/notebooks/${course.id}`} className="atlas-text-action">Open notebook</Link></div></article>)}</section>{!availableCourses.length && <EmptyState title="No published course sources are available yet." action={<Link to="/student/courses" className="button button-secondary">Explore courses</Link>}/>}</AppShell>;
  }
  return <AppShell><PageHeader eyebrow="Student workspace" title="Your notebooks" description="Collect sources, ask grounded questions, and turn learning into useful study tools." action={<Button onClick={create}><Plus size={16}/> New notebook</Button>}/><div className="notebook-library-toolbar"><div className="notebook-library-intro"><BookOpen size={21}/><span>Every notebook is a focused world for one subject, project, or curiosity.</span></div><label className="search-field"><Search size={16}/><span className="sr-only">Search notebooks</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search notebooks"/></label></div><div className="notebook-grid">{shown.map(notebook => <NotebookCard notebook={notebook} key={notebook.id}/>)}</div></AppShell>;
}
