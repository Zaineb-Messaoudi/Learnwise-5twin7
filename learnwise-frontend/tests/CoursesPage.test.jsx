import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CoursesPage } from '../src/features/student/pages/CoursesPage';
import { coursesApi } from '../src/api/courses.api';
import { analyticsApi } from '../src/api/analytics.api';
import { ThemeProvider } from '../src/contexts/ThemeContext';
import { AuthProvider } from '../src/contexts/AuthContext';

jest.mock('../src/api/courses.api', () => ({
  coursesApi: {
    catalog: jest.fn(),
  },
}));

jest.mock('../src/api/analytics.api', () => ({
  analyticsApi: {
    enroll: jest.fn(),
    enrollments: jest.fn(),
  },
}));

jest.mock('../src/api/client', () => ({
  isBackendApiEnabled: true,
}));

const mockCourses = [
  {
    id: 'course-1',
    title: 'Introduction to Machine Learning',
    description: 'Learn ML basics',
    level: 'Beginner',
    language: 'en',
    status: 'published',
    content_type: 'document',
    progress: { percentage: 60 },
    materials_count: 5,
  },
  {
    id: 'course-2',
    title: 'Advanced Python',
    description: 'Python for data science',
    level: 'Advanced',
    language: 'en',
    status: 'published',
    content_type: 'video',
    progress: { percentage: 100 },
    materials_count: 8,
  },
  {
    id: 'course-3',
    title: 'Web Development Basics',
    description: 'HTML CSS JS',
    level: 'Beginner',
    language: 'fr',
    status: 'draft',
    content_type: 'audio',
    progress: { percentage: 30 },
    materials_count: 3,
  },
];

const renderCoursesPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            <CoursesPage />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe('CoursesPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    coursesApi.catalog.mockResolvedValue(mockCourses);
    analyticsApi.enrollments.mockResolvedValue([
      {
        course: mockCourses[0],
        progress: { percentage: 60 },
      },
      {
        course: mockCourses[1],
        progress: { percentage: 100 },
      },
      {
        course: mockCourses[2],
        progress: { percentage: 30 },
      },
    ]);
  });

  test('renders course cards', async () => {
    renderCoursesPage();
    await waitFor(() => {
      expect(screen.getByText('Introduction to Machine Learning')).toBeInTheDocument();
    });
    expect(screen.getByText('Advanced Python')).toBeInTheDocument();
    expect(screen.getByText('Web Development Basics')).toBeInTheDocument();
  });

  test('filters courses by search query', async () => {
    renderCoursesPage();
    await waitFor(() => {
      expect(screen.getByText('Introduction to Machine Learning')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('Search courses');
    fireEvent.change(searchInput, { target: { value: 'Python' } });
    await waitFor(() => {
      expect(screen.getByText('Advanced Python')).toBeInTheDocument();
    });
    expect(screen.queryByText('Introduction to Machine Learning')).not.toBeInTheDocument();
  });

  test('filters courses by status', async () => {
    renderCoursesPage();
    await waitFor(() => {
      expect(screen.getByText('Introduction to Machine Learning')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Completed'));
    expect(screen.getByText('Advanced Python')).toBeInTheDocument();
    expect(screen.queryByText('Introduction to Machine Learning')).not.toBeInTheDocument();
  });

  test('shows empty state when no courses match', async () => {
    renderCoursesPage();
    await waitFor(() => {
      expect(screen.getByText('Introduction to Machine Learning')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('Search courses');
    fireEvent.change(searchInput, { target: { value: 'Nonexistent Course' } });
    await waitFor(() => {
      expect(screen.getByText('No courses match this view.')).toBeInTheDocument();
    });
  });

  test('course cards render with title and progress', async () => {
    renderCoursesPage();
    await waitFor(() => {
      expect(screen.getByText('Introduction to Machine Learning')).toBeInTheDocument();
    });
    expect(screen.getByText(/60%/)).toBeInTheDocument();
    expect(screen.getByText('Advanced Python')).toBeInTheDocument();
    expect(screen.getByText(/100%/)).toBeInTheDocument();
  });

  test('shows error state when catalog fails', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    coursesApi.catalog.mockRejectedValue(new Error('API error'));
    renderCoursesPage();
    await waitFor(() => {
      expect(screen.getByText('Course information could not be loaded.')).toBeInTheDocument();
    });
    consoleError.mockRestore();
  });
});
