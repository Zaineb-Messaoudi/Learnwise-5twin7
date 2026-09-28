import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { assistantApi } from '../src/api/assistant.api';
import { coursesApi } from '../src/api/courses.api';
import { materialsApi } from '../src/api/materials.api';
import { quizzesApi } from '../src/api/quizzes.api';
import { NotebookWorkspacePage } from '../src/features/student/pages/NotebookWorkspacePage';

jest.mock('../src/api/client', () => ({ isBackendApiEnabled: true }));
jest.mock('../src/layouts/AppShell', () => ({ AppShell: ({ children }) => <div>{children}</div> }));
jest.mock('../src/components/shared/Primitives', () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
  PageHeader: ({ title }) => <h1>{title}</h1>,
}));
jest.mock('../src/components/ui/States', () => ({
  ErrorState: ({ message }) => <p>{message}</p>,
  LoadingState: ({ label }) => <p>{label}</p>,
}));
jest.mock('../src/api/courses.api', () => ({ coursesApi: { detail: jest.fn() } }));
jest.mock('../src/api/materials.api', () => ({ materialsApi: { list: jest.fn(), processingStatus: jest.fn(), upload: jest.fn() } }));
jest.mock('../src/api/assistant.api', () => ({
  assistantApi: { sessions: jest.fn(), createSession: jest.fn(), messages: jest.fn(), ask: jest.fn() },
}));
jest.mock('../src/api/quizzes.api', () => ({ quizzesApi: { generate: jest.fn(), generation: jest.fn() } }));
jest.mock('../src/features/student/data/notebookStore', () => ({ getNotebooks: () => [] }));

describe('backend notebook integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    coursesApi.detail.mockResolvedValue({ id: 'course-7', title: 'Neural Networks', description: 'Course overview' });
    materialsApi.list.mockResolvedValue({ results: [{ id: 'material-4', title: 'Backpropagation.pdf', status: 'completed' }] });
    assistantApi.sessions.mockResolvedValue({ results: [] });
    assistantApi.createSession.mockResolvedValue({ id: 'session-2' });
    assistantApi.messages.mockResolvedValue({ results: [] });
    assistantApi.ask.mockResolvedValue({
      assistant_message: {
        id: 'answer-1',
        role: 'assistant',
        content: 'Gradient descent updates model weights.',
        citations: [{ id: 'material-4', title: 'Backpropagation.pdf', page: 4 }],
      },
    });
    quizzesApi.generate.mockResolvedValue({
      id: 'generation-1',
      status: 'completed',
      result: { id: 'quiz-1', title: 'Generated quiz', questions: [{ prompt: 'What is gradient descent?' }] },
    });
  });

  test('opens a course notebook and sends selected Django material IDs to the assistant', async () => {
    render(<MemoryRouter initialEntries={['/student/notebooks/course-7']}>
      <Routes><Route path="/student/notebooks/:notebookId" element={<NotebookWorkspacePage/>}/></Routes>
    </MemoryRouter>);

    expect(await screen.findByRole('heading', { name: 'Neural Networks' })).toBeInTheDocument();
    expect(assistantApi.createSession).toHaveBeenCalledWith({ title: 'Neural Networks', course_id: 'course-7' });
    fireEvent.click(screen.getByRole('button', { name: 'What are the key ideas?' }));

    expect(await screen.findByText('Gradient descent updates model weights.')).toBeInTheDocument();
    await waitFor(() => expect(assistantApi.ask).toHaveBeenCalledWith('session-2', {
      content: 'What are the key ideas?',
      course_id: 'course-7',
      material_ids: ['material-4'],
    }));
    expect(screen.getByRole('button', { name: /Backpropagation.pdf · p. 4/ })).toBeInTheDocument();
  });

  test('generates a quiz draft from the selected course materials', async () => {
    render(<MemoryRouter initialEntries={['/student/notebooks/course-7']}>
      <Routes><Route path="/student/notebooks/:notebookId" element={<NotebookWorkspacePage/>}/></Routes>
    </MemoryRouter>);

    await screen.findByRole('heading', { name: 'Neural Networks' });
    fireEvent.click(screen.getByRole('button', { name: /Quiz/ }));

    expect(await screen.findByText(/What is gradient descent\?/)).toBeInTheDocument();
    expect(quizzesApi.generate).toHaveBeenCalledWith({
      course_id: 'course-7',
      material_ids: ['material-4'],
      kind: 'quiz',
      question_count: 5,
      difficulty: 'medium',
    });
  });
});
