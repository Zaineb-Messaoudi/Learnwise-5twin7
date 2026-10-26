import { resolveWorkspaceView } from '../src/routes/AppRoutes';
import React, { Suspense } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { AtlasDashboardPage } from '../src/features/student/pages/AtlasDashboardPage';
import { ThemeProvider } from '../src/contexts/ThemeContext';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../src/contexts/AuthContext';
import { RouteOverrides } from '../src/routes/AppRoutes';

jest.mock('../src/api/client', () => ({ apiRequest: jest.fn(), isBackendApiEnabled: false }));

describe('workspace route resolution', () => {
  test('lazy-loads the public homepage route', async () => {
    render(<MemoryRouter initialEntries={['/']}><Suspense fallback={<p>Loading page</p>}><RouteOverrides/></Suspense></MemoryRouter>);
    expect(await screen.findByRole('heading', { level: 1, name: /aha moment/i }, { timeout: 30000 })).toBeInTheDocument();
  });

  test.each([
    ['/student/quizzes/demo/attempt', 'quiz-attempt'],
    ['/student/quizzes/demo/result', 'quiz-result'],
    ['/student/courses/ai-101', 'course-detail'],
    ['/student/courses/ai-101/player', 'course-player'],
    ['/student/exercises/demo', 'exercise-detail'],
    ['/student/assistant/demo', 'assistant'],
    ['/student/notebooks', 'notebook-library'],
    ['/student/notebooks/neural-networks', 'notebook-workspace'],
    ['/student/search', 'search'],
    ['/teacher/ai-generation', 'teacher-ai-generation', 'teacher'],
    ['/admin/activity', 'admin-activity', 'admin'],
    ['/admin/notifications', 'admin-notifications', 'admin'],
  ])('%s resolves to %s', (path, expected, role = 'student') => {
    expect(resolveWorkspaceView(path, role)).toBe(expected);
  });

  describe('student dashboard learning map', () => {
    test('shows a connected, labeled learning path with a clear next step', () => {
      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      render(<QueryClientProvider client={queryClient}><AuthProvider><ThemeProvider><MemoryRouter><AtlasDashboardPage /></MemoryRouter></ThemeProvider></AuthProvider></QueryClientProvider>);
      expect(screen.getByText(/3 connected steps/i)).toBeInTheDocument();
      expect(screen.getByText('Neural networks')).toBeInTheDocument();
      expect(screen.getByText('Backpropagation').closest('[aria-current="step"]')).toBeInTheDocument();
      expect(screen.getByText('3-question practice')).toBeInTheDocument();
      expect(document.querySelector('.command-map-path')).toBeInTheDocument();
    });
  });

  test('does not let the student prefix swallow specific workflows', () => {
    expect(resolveWorkspaceView('/student/quizzes/demo/attempt')).not.toBe('detail');
  });
});
