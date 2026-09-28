import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '../src/contexts/ThemeContext';
import { AuthProvider } from '../src/contexts/AuthContext';
import { QuizAttemptPage } from '../src/features/student/pages/QuizAttemptPage';
import { QuizResultPage } from '../src/features/student/pages/QuizResultPage';

jest.mock('../src/api/client', () => ({ apiRequest: jest.fn(), isBackendApiEnabled: false }));

function renderQuiz(initialPath = '/student/quizzes/demo/attempt') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}><AuthProvider><ThemeProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/student/quizzes/:id/attempt" element={<QuizAttemptPage />} />
          <Route path="/student/quizzes/:id/result" element={<QuizResultPage />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider></AuthProvider></QueryClientProvider>
  );
}

describe('quiz attempt workflow', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.removeItem('learnwise:theme');
  });

  it('keeps selected answers and shows the calculated submitted result', async () => {
    const user = userEvent.setup();
    renderQuiz();

    await user.click(screen.getByLabelText('To add non-linearity to the network'));
    await user.click(screen.getByRole('button', { name: 'Next question' }));
    await user.click(screen.getByLabelText('The model weights'));
    await user.click(screen.getByRole('button', { name: 'Previous' }));
    expect(screen.getByLabelText('To add non-linearity to the network')).toBeChecked();

    await user.click(screen.getByRole('button', { name: 'Question 2' }));
    await user.click(screen.getByRole('button', { name: 'Question 3' }));
    await user.click(screen.getByLabelText('A closer prediction'));
    await user.click(screen.getByRole('button', { name: 'Question 4' }));
    await user.click(screen.getByLabelText('To check generalization'));
    await user.click(screen.getByRole('button', { name: 'Submit quiz' }));
    await user.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(screen.getByLabelText('Quiz score')).toHaveTextContent('100%');
    expect(JSON.parse(window.sessionStorage.getItem('learnwise:quiz-result:demo'))).toMatchObject({ score: 4, total: 4 });
  });

  it('does not invent a score for a result page without a completed attempt', () => {
    renderQuiz('/student/quizzes/demo/result');

    expect(screen.getByText('No completed attempt found.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Quiz score')).not.toBeInTheDocument();
  });
});
