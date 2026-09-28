import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '../src/contexts/ThemeContext';
import { AuthProvider } from '../src/contexts/AuthContext';
import { QuizAttemptPage } from '../src/features/student/pages/QuizAttemptPage';
import { QuizResultPage } from '../src/features/student/pages/QuizResultPage';

jest.mock('../src/api/client', () => ({ apiRequest: jest.fn(), isBackendApiEnabled: true }));
jest.mock('../src/api/quizzes.api', () => ({
  quizzesApi: {
    detail: jest.fn(),
    startAttempt: jest.fn(),
    saveAttempt: jest.fn(),
    submit: jest.fn(),
    result: jest.fn(),
  },
}));

import { quizzesApi } from '../src/api/quizzes.api';

function renderBackendQuiz() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><AuthProvider><ThemeProvider><MemoryRouter initialEntries={['/student/quizzes/quiz-1/attempt']}><Routes><Route path="/student/quizzes/:id/attempt" element={<QuizAttemptPage/>}/><Route path="/student/quizzes/:id/result" element={<QuizResultPage/>}/></Routes></MemoryRouter></ThemeProvider></AuthProvider></QueryClientProvider>);
}

describe('backend assessment attempt', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    quizzesApi.detail.mockResolvedValue({ id: 'quiz-1', title: 'Course check-in', questions: [{ id: 'question-1', text: 'Select the correct answer', choices: [{ id: 'choice-a', text: 'Correct option' }, { id: 'choice-b', text: 'Other option' }] }] });
    quizzesApi.startAttempt.mockResolvedValue({ id: 'attempt-1', answers: {} });
    quizzesApi.saveAttempt.mockResolvedValue({ id: 'attempt-1' });
    quizzesApi.submit.mockResolvedValue({ score: 1, correct_answers: 1, total_questions: 1, question_feedback: [{ question_id: 'question-1', question: 'Select the correct answer', is_correct: true, feedback: 'Correct.' }] });
  });

  it('starts, saves, submits and displays the backend evaluation', async () => {
    const user = userEvent.setup();
    renderBackendQuiz();
    await user.click(await screen.findByLabelText('Correct option'));
    await user.click(screen.getByRole('button', { name: 'Submit quiz' }));
    await user.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(await screen.findByLabelText('Quiz score')).toHaveTextContent('100%');
    await waitFor(() => expect(quizzesApi.saveAttempt).toHaveBeenCalledWith('quiz-1', 'attempt-1', { 'question-1': 'choice-a' }));
    expect(quizzesApi.submit).toHaveBeenCalledWith('quiz-1', 'attempt-1', { 'question-1': 'choice-a' });
    expect(screen.getByText('Correct.')).toBeInTheDocument();
  });
});
