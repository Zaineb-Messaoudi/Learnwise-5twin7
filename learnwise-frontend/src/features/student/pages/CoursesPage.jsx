import { useMemo, useState } from 'react';
import { AlertCircle, BookOpen, Plus, Search } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { analyticsApi } from '../../../api/analytics.api';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { CourseCard } from '../components/CourseCard';
import { EmptyState, ErrorState, LoadingState } from '../../../components/ui/States';
import '../components/courses.css';
import { CourseFilters } from '../components/CourseFilters';

CoursesPage.propTypes = {};

function itemsFrom(response) {
  return Array.isArray(response) ? response : response?.results || [];
}

function mapCourse(course, progress = 0) {
  return {
    ...course,
    id: course.id,
    title: course.title || 'Untitled course',
    description: course.description || '',
    instructor: course.instructor_name || course.teacher_name || 'Learnwise educator',
    level: course.level || 'All levels',
    progress: Number(
      course?.progress?.percentage ??
        course?.progress?.completion_percentage ??
        (typeof course.progress === 'number' ? course.progress : undefined) ??
        progress?.percentage ??
        progress?.completion_percentage ??
        (typeof progress === 'number' ? progress : 0),
    ),
    lessons: course.materials_count ?? course.lessons_count ?? 0,
    category: course.category || course.language || 'Course',
    icon: course.icon || '✦',
  };
}

export function CoursesPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('All courses');
  const [query, setQuery] = useState('');
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterLevel, setFilterLevel] = useState('all');
  const [filterContentType, setFilterContentType] = useState('all');
  const [filterLanguage, setFilterLanguage] = useState('all');

  const catalogQuery = useQuery({
    queryKey: ['content', 'course-catalog', filterStatus, filterLevel, filterContentType, filterLanguage, query],
    queryFn: () =>
      coursesApi.catalog(`status=${filterStatus}&level=${filterContentType}&language=${filterLanguage}`),
    enabled: isBackendApiEnabled,
  });

  const enrollmentQuery = useQuery({
    queryKey: ['analytics', 'enrollments'],
    queryFn: analyticsApi.enrollments,
    enabled: isBackendApiEnabled,
  });

  const enrollMutation = useMutation({
    mutationFn: analyticsApi.enroll,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['analytics', 'enrollments'] }),
  });

  const catalog = useMemo(() => itemsFrom(catalogQuery.data).map(mapCourse), [catalogQuery.data]);

  const enrolled = useMemo(() => {
    if (!isBackendApiEnabled) {return [];}
    return itemsFrom(enrollmentQuery.data).map((item) => {
      const sourceCourse =
        typeof item.course === 'object' && item.course
          ? item.course
          : catalog.find((course) => String(course.id) === String(item.course || item.course_id));
      return mapCourse(
        sourceCourse || {
          id: item.course || item.course_id,
          title: item.course_title,
          level: item.level,
        },
        item.progress,
      );
    });
  }, [enrollmentQuery.data, catalog]);

  const enrolledIds = new Set(enrolled.map((course) => String(course.id)));
  const source = catalogOpen && isBackendApiEnabled ? catalog.filter((course) => !enrolledIds.has(String(course.id))) : enrolled;

  const shown = useMemo(
    () =>
      source.filter((course) => {
        const matchesSearch = course.title.toLowerCase().includes(query.toLowerCase());
        const matchesFilter =
          filter === 'All courses' || (filter === 'Completed' ? course.progress >= 100 : course.progress < 100);
        const matchesStatus = !filterStatus || filterStatus === 'all' || course.status === filterStatus;
        const matchesLevel = !filterLevel || filterLevel === 'all' || course.level === filterLevel;
        const matchesContentType = !filterContentType || filterContentType === 'all' || course.category === filterContentType;
        const matchesLanguage = !filterLanguage || filterLanguage === 'all' || course.language === filterLanguage;
        return matchesSearch && matchesFilter && matchesStatus && matchesLevel && matchesContentType && matchesLanguage;
      }),
    [source, filter, query, filterStatus, filterLevel, filterContentType, filterLanguage],
  );

  const loading = isBackendApiEnabled && (catalogQuery.isLoading || enrollmentQuery.isLoading);
  const failed = isBackendApiEnabled && (catalogQuery.isError || enrollmentQuery.isError);

  if (loading) {
    return (
      <AppShell>
        <PageHeader eyebrow="My learning" title="Your courses" />
        <LoadingState label="Loading your courses and enrollments" />
      </AppShell>
    );
  }

  if (failed) {
    return (
      <AppShell>
        <PageHeader eyebrow="My learning" title="Your courses" />
        <ErrorState
          message="Course information could not be loaded."
          action={
            <Button onClick={() => { void catalogQuery.refetch(); void enrollmentQuery.refetch(); }}>Retry</Button>
          }
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow={catalogOpen ? 'Course catalog' : 'My learning'}
        title={catalogOpen ? 'Find your next course.' : 'Your courses'}
        description={
          catalogOpen
            ? 'Explore published courses and add one to your learning path.'
            : 'Keep building your knowledge, one lesson at a time.'
        }
        action={
          <Button
            variant={catalogOpen ? 'secondary' : 'primary'}
            onClick={() => {
              setCatalogOpen((value) => !value);
              setFilter('All courses');
              setQuery('');
            }}
          >
            {catalogOpen ? (
              <>
                <BookOpen size={16} />
                My courses
              </>
            ) : (
              <>
                <Plus size={16} />
                Explore courses
              </>
            )}
          </Button>
        }
      />
      <div className="toolbar">
        <CourseFilters
          filterStatus={filterStatus}
          setFilterStatus={setFilterStatus}
          filterLevel={filterLevel}
          setFilterLevel={setFilterLevel}
          filterContentType={filterContentType}
          setFilterContentType={setFilterContentType}
          filterLanguage={filterLanguage}
          setFilterLanguage={setFilterLanguage}
          onApplyFilters={() => {}}
        />
        <details className="segmented" aria-label="Course status" open={filter === 'All courses'}>
          {['All courses', 'In progress', 'Completed'].map((option) => (
            <button
              type="button"
              key={option}
              className={filter === option ? 'selected' : ''}
              aria-pressed={filter === option}
              onClick={() => setFilter(option)}
            >
              {option}
            </button>
          ))}
        </details>
        <label className="search-field">
          <Search size={16} />
          <span className="sr-only">Search courses</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search courses" />
        </label>
      </div>
      {enrollMutation.isError && (
        <p className="upload-error" role="alert">
          <AlertCircle size={15} /> Enrollment failed. Try again.
        </p>
      )}
      {shown.length ? (
        <div className="course-grid large-grid">
          {shown.map((course) => (
            <CourseCard key={course.id} course={course} />
          ))}
        </div>
      ) : (
        <EmptyState
          title={catalogOpen ? 'No new courses are available right now.' : 'No courses match this view.'}
          action={
            catalogOpen ? null : (
              <Button variant="secondary" onClick={() => setCatalogOpen(true)}>
                Explore courses
              </Button>
            )
          }
        />
      )}
    </AppShell>
  );
}
