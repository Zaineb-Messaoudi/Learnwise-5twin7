import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CourseDetailPage } from '../src/features/student/pages/CourseDetailPage';
import { coursesApi } from '../src/api/courses.api';
import { materialsApi } from '../src/api/materials.api';
import { analyticsApi } from '../src/api/analytics.api';
import { quizzesApi } from '../src/api/quizzes.api';
import { ThemeProvider } from '../src/contexts/ThemeContext';
import { AuthProvider } from '../src/contexts/AuthContext';
import { usePresence } from '../src/api/presence.api';

jest.mock('../src/api/courses.api', () => ({
  coursesApi: { detail: jest.fn() },
}));

jest.mock('../src/api/materials.api', () => ({
  materialsApi: {
    list: jest.fn(),
    transcription: jest.fn(),
    summary: jest.fn(),
    download: jest.fn(),
  },
}));

jest.mock('../src/api/analytics.api', () => ({
  analyticsApi: {
    startLearningSession: jest.fn(),
    recordActivity: jest.fn(),
    finishLearningSession: jest.fn(),
  },
}));

jest.mock('../src/api/quizzes.api', () => ({
  quizzesApi: {
    generate: jest.fn(),
    generation: jest.fn(),
    create: jest.fn(),
  },
}));

jest.mock('../src/api/client', () => ({
  isBackendApiEnabled: true,
}));

jest.mock('../src/api/presence.api', () => ({
  usePresence: jest.fn(() => ({ totalActive: 0 })),
}));

jest.mock('../src/layouts/AppShell', () => ({
  AppShell: ({ children }) => <>{children}</>,
}));

const mockCourse = {
  id: 'ai-101',
  title: 'Neural networks basics',
  description: 'Learn how neural networks work',
  level: 'Intermediate',
  language: 'en',
  status: 'published',
  content_type: 'document',
  progress: { percentage: 45 },
  materials_count: 2,
};

const mockMaterials = [
  {
    id: 'mat-1',
    title: 'Foundations',
    kind: 'document',
    status: 'completed',
    file: '/media/foundations.pdf',
  },
  {
    id: 'mat-2',
    title: 'Backpropagation',
    kind: 'audio',
    status: 'completed',
    file: '/media/backprop.mp3',
  },
];

const renderPage = (props = {}) => {
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
            <CourseDetailPage {...props} />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe('CourseDetailPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    coursesApi.detail.mockResolvedValue(mockCourse);
    materialsApi.list.mockResolvedValue(mockMaterials);

    materialsApi.summary.mockResolvedValue({
      text: 'Lesson summary',
    });

    materialsApi.transcription.mockResolvedValue({
      text: 'Lesson transcript',
    });

    quizzesApi.generate.mockResolvedValue({
      id: 'gen-1',
    });

    quizzesApi.generation.mockResolvedValue({
      id: 'gen-1',
      status: 'completed',
      questions: [
        {
          prompt: 'What is a neural network?',
          explanation: 'A computing system',
          choices: [
            {
              text: 'A computing system',
              is_correct: true,
            },
            {
              text: 'A type of bread',
              is_correct: false,
            },
          ],
        },
      ],
    });

    quizzesApi.create.mockResolvedValue({
      id: 'quiz-1',
    });

    usePresence.mockReturnValue({
      totalActive: 0,
    });
  });

  test('renders course details', async () => {
    renderPage();

    expect(
  await screen.findByRole('heading', {
    level: 1,
    name: 'Neural networks basics',
  })
).toBeInTheDocument();

    expect(
      screen.getByText('Learn how neural networks work')
    ).toBeInTheDocument();
  });

  test('renders course materials', async () => {
    renderPage();

    expect(
      await screen.findByText('Foundations')
    ).toBeInTheDocument();

    expect(
      screen.getByText('Backpropagation')
    ).toBeInTheDocument();
  });

  test('selects a material and shows viewer', async () => {
  renderPage({ player: true });

  const materialButton = await screen.findByRole('button', {
    name: /Foundations.*document.*completed/i,
  });

  fireEvent.click(materialButton);

  expect(
    await screen.findByText('Course document')
  ).toBeInTheDocument();

  expect(
    screen.getByRole('heading', {
      level: 3,
      name: 'Foundations',
    })
  ).toBeInTheDocument();
});

  test('starts learning session when button clicked', async () => {
    analyticsApi.startLearningSession.mockResolvedValue({
      id: 'session-1',
    });

    renderPage({ player: true });

    const startBtn = await screen.findByRole('button', {
      name: /Start learning session/,
    });

    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(
        analyticsApi.startLearningSession
      ).toHaveBeenCalledWith('ai-101');

      expect(
        screen.getByText('Complete session')
      ).toBeInTheDocument();
    });
  });

  test('completes learning session', async () => {
    analyticsApi.startLearningSession.mockResolvedValue({
      id: 'session-1',
    });

    analyticsApi.recordActivity.mockResolvedValue({});
    analyticsApi.finishLearningSession.mockResolvedValue({});

    renderPage({ player: true });

    const startBtn = await screen.findByRole('button', {
      name: /Start learning session/,
    });

    fireEvent.click(startBtn);

    const completeBtn = await screen.findByRole('button', {
      name: /Complete session/,
    });

    fireEvent.click(completeBtn);

    await waitFor(() => {
      expect(
        analyticsApi.finishLearningSession
      ).toHaveBeenCalledWith('session-1');
    });
  });

  test('shows loading state', () => {
    coursesApi.detail.mockReturnValue(new Promise(() => {}));
    materialsApi.list.mockReturnValue(new Promise(() => {}));

    renderPage();

    expect(
      screen.getByText(/Loading course content/)
    ).toBeInTheDocument();
  });

  test('shows error state when course request fails', async () => {
    coursesApi.detail.mockRejectedValue(
      new Error('Failed to load course')
    );

    renderPage();

    expect(
      await screen.findByText('This course could not be opened.')
    ).toBeInTheDocument();
  });

  test('retries failed course requests', async () => {
    coursesApi.detail.mockRejectedValueOnce(
      new Error('Temporary failure')
    );

    renderPage();

    const retryButton = await screen.findByRole('button', {
      name: /Retry/i,
    });

    coursesApi.detail.mockResolvedValue(mockCourse);

    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(coursesApi.detail).toHaveBeenCalledTimes(2);
    });
  });

  test('starts quiz generation', async () => {
    renderPage();

    const generateButton = await screen.findByRole('button', {
      name: /Generate Practice Quiz/,
    });

    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(quizzesApi.generate).toHaveBeenCalled();
    });
  });

  test('creates a quiz after successful generation', async () => {
    renderPage();

    fireEvent.click(
      await screen.findByRole('button', {
        name: /Generate Practice Quiz/,
      })
    );

    await waitFor(() => {
      expect(quizzesApi.create).toHaveBeenCalled();
    });
  });

  test('shows quiz generation success message', async () => {
    renderPage();

    fireEvent.click(
      await screen.findByRole('button', {
        name: /Generate Practice Quiz/,
      })
    );

    expect(
      await screen.findByText(/Practice quiz created!/)
    ).toBeInTheDocument();
  });

  test('shows quiz generation error', async () => {
    quizzesApi.generate.mockRejectedValue(
      new Error('Quiz service unavailable')
    );

    renderPage();

    fireEvent.click(
      await screen.findByRole('button', {
        name: /Generate Practice Quiz/,
      })
    );

    expect(
      await screen.findByText('Quiz service unavailable')
    ).toBeInTheDocument();
  });

  test('shows student presence when students are active', async () => {
    usePresence.mockReturnValue({
      totalActive: 3,
    });

    renderPage();

    expect(
      await screen.findByText('3 students online')
    ).toBeInTheDocument();
  });

  test('shows singular student presence', async () => {
    usePresence.mockReturnValue({
      totalActive: 1,
    });

    renderPage();

    expect(
      await screen.findByText('1 student online')
    ).toBeInTheDocument();
  });

  test('disables session start while request is pending', async () => {
    let resolveSession;

    analyticsApi.startLearningSession.mockReturnValue(
      new Promise(resolve => {
        resolveSession = resolve;
      })
    );

    renderPage({ player: true });

    const startBtn = await screen.findByRole('button', {
      name: /Start learning session/,
    });

    fireEvent.click(startBtn);

    expect(
      await screen.findByRole('button', {
        name: /Starting/,
      })
    ).toBeDisabled();

    resolveSession({ id: 'session-1' });

    await waitFor(() => {
      expect(
        screen.getByText('Complete session')
      ).toBeInTheDocument();
    });
  });

  
  test('shows an error if starting a learning session fails', async () => {
    analyticsApi.startLearningSession.mockRejectedValue(
      new Error('Session failed')
    );

    renderPage({ player: true });

    fireEvent.click(
      await screen.findByRole('button', {
        name: /Start learning session/,
      })
    );

    expect(
      await screen.findByText(
        'Could not start or track this learning session. Retry before continuing.'
      )
    ).toBeInTheDocument();
  });

  test('shows an error if finishing a learning session fails', async () => {
    analyticsApi.startLearningSession.mockResolvedValue({
      id: 'session-1',
    });

    analyticsApi.recordActivity.mockResolvedValue({});
    analyticsApi.finishLearningSession.mockRejectedValue(
      new Error('Finish failed')
    );

    renderPage({ player: true });

    fireEvent.click(
      await screen.findByRole('button', {
        name: /Start learning session/,
      })
    );

    fireEvent.click(
      await screen.findByRole('button', {
        name: /Complete session/,
      })
    );

    expect(
      await screen.findByText(
        'Could not finish this learning session. Your progress event may still be pending; retry to close it.'
      )
    ).toBeInTheDocument();
  });

  test('loads material summary', async () => {
    renderPage({ player: true });

    expect(
      await screen.findByText('AI Summary')
    ).toBeInTheDocument();

    expect(
      screen.getByText('Lesson summary')
    ).toBeInTheDocument();
  });

  test('loads audio transcript for audio material', async () => {
    renderPage({ player: true });

    fireEvent.click(
      await screen.findByText('Backpropagation')
    );

    await waitFor(() => {
      expect(materialsApi.transcription).toHaveBeenCalledWith('mat-2');
    });
  });

  test('shows retry state when materials request fails', async () => {
    materialsApi.list.mockRejectedValue(
      new Error('Materials unavailable')
    );

    renderPage();

    expect(
      await screen.findByText('This course could not be opened.')
    ).toBeInTheDocument();
  });

  test('renders course progress', async () => {
    renderPage();

    expect(
      await screen.findByText('45%')
    ).toBeInTheDocument();
  });

  test('uses course ID from route params', async () => {
    render(
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: {
              queries: { retry: false },
            },
          })
        }
      >
        <ThemeProvider>
          <AuthProvider>
            <MemoryRouter
              initialEntries={['/student/courses/custom-course']}
            >
              <CourseDetailPage />
            </MemoryRouter>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(coursesApi.detail).toHaveBeenCalledWith('ai-101');
    });
  });
});
