import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../src/contexts/ThemeContext';
import { AuthProvider } from '../src/contexts/AuthContext';
import { AssessmentStudioPage } from '../src/features/staff/pages/AssessmentStudioPage';

jest.mock('../src/api/client', () => ({ apiRequest: jest.fn(), isBackendApiEnabled: true }));
jest.mock('../src/api/courses.api', () => ({ coursesApi: { list: jest.fn() } }));
jest.mock('../src/api/quizzes.api', () => ({
  quizzesApi: { generate: jest.fn(), generation: jest.fn(), create: jest.fn(), update: jest.fn(), publish: jest.fn() },
}));
jest.mock('../src/api/exercises.api', () => ({
  exercisesApi: { create: jest.fn(), update: jest.fn(), remove: jest.fn(), publish: jest.fn() },
}));

import { coursesApi } from '../src/api/courses.api';
import { quizzesApi } from '../src/api/quizzes.api';
import { exercisesApi } from '../src/api/exercises.api';

// Ce que renvoie le backend une fois la génération terminée (format réel de GET /generations/<id>/).
const generatedQuestions = [
  { prompt: 'First question?', choices: [{ text: 'a1', is_correct: true }, { text: 'a2', is_correct: false }, { text: 'a3', is_correct: false }, { text: 'a4', is_correct: false }], correct_index: 0, explanation: 'Because one.' },
  { prompt: 'Second question?', choices: [{ text: 'b1', is_correct: false }, { text: 'b2', is_correct: false }, { text: 'b3', is_correct: true }, { text: 'b4', is_correct: false }], correct_index: 2, explanation: 'Because two.' },
];
const completedJob = { id: '7', status: 'completed', result: { questions: generatedQuestions } };

function renderStudio() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><AuthProvider><ThemeProvider><MemoryRouter><AssessmentStudioPage /></MemoryRouter></ThemeProvider></AuthProvider></QueryClientProvider>);
}

// Lance une génération et attend que le brouillon apparaisse.
async function generateDraft(user, kind) {
  await screen.findByRole('option', { name: 'Anglais' });
  if (kind === 'exercise') await user.selectOptions(screen.getByLabelText('Assessment type'), 'exercise');
  await user.click(screen.getByRole('button', { name: kind === 'exercise' ? /Generate exercises/ : /Generate quiz/ }));
  await screen.findByText('2 draft questions');
}

describe('teacher assessment studio with the real backend', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    coursesApi.list.mockResolvedValue({ results: [{ id: 1, title: 'Anglais' }] });
    quizzesApi.generate.mockResolvedValue(completedJob);
    quizzesApi.create.mockResolvedValue({ id: 'quiz-9' });
    quizzesApi.publish.mockResolvedValue({ id: 'quiz-9', status: 'published' });
    let nextId = 0;
    exercisesApi.create.mockImplementation(async () => ({ id: `ex-${++nextId}` }));
    exercisesApi.update.mockImplementation(async id => ({ id }));
    exercisesApi.remove.mockResolvedValue('');
    exercisesApi.publish.mockImplementation(async id => ({ id, status: 'published' }));
  });

  it('sends the generation request in the format the backend expects', async () => {
    const user = userEvent.setup();
    renderStudio();
    await generateDraft(user, 'quiz');
    expect(quizzesApi.generate).toHaveBeenCalledWith({
      course_id: 1, source_text: 'Neural networks · Chapter 4', kind: 'quiz', question_count: 3, difficulty: 'medium',
    });
    expect(screen.getAllByLabelText('Question')[0]).toHaveValue('First question?'); // le brouillon est éditable
  });

  it('saves and publishes a quiz as one quiz with all its questions', async () => {
    const user = userEvent.setup();
    renderStudio();
    await generateDraft(user, 'quiz');
    await user.click(screen.getByRole('button', { name: /Publish/ }));
    await waitFor(() => expect(quizzesApi.publish).toHaveBeenCalledWith('quiz-9'));
    expect(quizzesApi.create).toHaveBeenCalledTimes(1);
    const payload = quizzesApi.create.mock.calls[0][0];
    expect(payload.questions).toHaveLength(2);
    expect(payload.questions[1].choices.map(choice => choice.is_correct)).toEqual([false, false, true, false]);
    expect(exercisesApi.create).not.toHaveBeenCalled();
  });

  it('creates ONE exercise per question, in the shape the exercises endpoint expects, then publishes each', async () => {
    const user = userEvent.setup();
    renderStudio();
    await generateDraft(user, 'exercise');
    await user.click(screen.getByRole('button', { name: /Publish/ }));
    await waitFor(() => expect(exercisesApi.publish).toHaveBeenCalledTimes(2));

    expect(exercisesApi.create).toHaveBeenCalledTimes(2);
    const [first, second] = exercisesApi.create.mock.calls.map(call => call[0]);
    expect(first).toEqual({
      course_id: 1,
      title: 'Neural networks · Chapter 4 · 1',
      prompt: 'First question?',
      explanation: 'Because one.',
      choices: [{ text: 'a1', is_correct: true }, { text: 'a2', is_correct: false }, { text: 'a3', is_correct: false }, { text: 'a4', is_correct: false }],
    });
    expect(second.title).toBe('Neural networks · Chapter 4 · 2');
    expect(second.choices.map(choice => choice.is_correct)).toEqual([false, false, true, false]);
    expect(first).not.toHaveProperty('questions'); // l'ancien format (quiz) était refusé par /exercises/
    expect(exercisesApi.publish).toHaveBeenCalledWith('ex-1');
    expect(exercisesApi.publish).toHaveBeenCalledWith('ex-2');
    expect(quizzesApi.create).not.toHaveBeenCalled();
  });

  it('updates the saved exercises instead of creating duplicates on the next save', async () => {
    const user = userEvent.setup();
    renderStudio();
    await generateDraft(user, 'exercise');
    await user.click(screen.getByRole('button', { name: /Save draft/ }));
    await waitFor(() => expect(exercisesApi.create).toHaveBeenCalledTimes(2));

    await user.type(screen.getAllByLabelText('Question')[0], ' (edited)');
    await user.click(screen.getByRole('button', { name: /Save draft/ }));
    await waitFor(() => expect(exercisesApi.update).toHaveBeenCalledTimes(2));
    expect(exercisesApi.create).toHaveBeenCalledTimes(2); // pas de doublons
    expect(exercisesApi.update).toHaveBeenCalledWith('ex-1', expect.objectContaining({ prompt: 'First question? (edited)' }));
    expect(exercisesApi.update).toHaveBeenCalledWith('ex-2', expect.objectContaining({ prompt: 'Second question?' }));
  });

  it('deletes the saved exercise of a question the teacher removed', async () => {
    const user = userEvent.setup();
    renderStudio();
    await generateDraft(user, 'exercise');
    await user.click(screen.getByRole('button', { name: /Save draft/ }));
    await waitFor(() => expect(exercisesApi.create).toHaveBeenCalledTimes(2));

    await user.click(screen.getByRole('button', { name: 'Remove question 1' }));
    await user.click(screen.getByRole('button', { name: /Save draft/ }));
    await waitFor(() => expect(exercisesApi.remove).toHaveBeenCalledWith('ex-1'));
    expect(exercisesApi.update).toHaveBeenCalledTimes(1);
    // la question restante est renumérotée "· 1" et garde son exercice
    expect(exercisesApi.update).toHaveBeenCalledWith('ex-2', expect.objectContaining({ title: 'Neural networks · Chapter 4 · 1' }));
  });

  it('keeps the ids of exercises already created when a later one fails, so a retry makes no duplicates', async () => {
    const user = userEvent.setup();
    renderStudio();
    await generateDraft(user, 'exercise');
    exercisesApi.create
      .mockResolvedValueOnce({ id: 'ex-A' })
      .mockRejectedValueOnce(new Error('Server hiccup'));
    await user.click(screen.getByRole('button', { name: /Save draft/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Server hiccup');

    exercisesApi.create.mockResolvedValueOnce({ id: 'ex-B' });
    await user.click(screen.getByRole('button', { name: /Save draft/ }));
    await waitFor(() => expect(exercisesApi.create).toHaveBeenCalledTimes(3));
    expect(exercisesApi.update).toHaveBeenCalledWith('ex-A', expect.anything()); // la 1re question est mise à jour, pas recréée
  });

  it('keeps polling while the AI is still working, then shows the draft', async () => {
    quizzesApi.generate.mockResolvedValue({ id: '7', status: 'queued' });
    quizzesApi.generation.mockResolvedValue(completedJob);
    const user = userEvent.setup();
    renderStudio();
    await screen.findByRole('option', { name: 'Anglais' });
    await user.click(screen.getByRole('button', { name: /Generate quiz/ }));
    // la page interroge le serveur toutes les 1,5 s : on attend plus longtemps que le délai par défaut (1 s)
    expect(await screen.findByText('2 draft questions', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(quizzesApi.generation).toHaveBeenCalledWith('7');
  });

  it('shows the readable error message when the generation fails', async () => {
    quizzesApi.generate.mockResolvedValue({ id: '7', status: 'failed', error_message: 'The AI service is busy or its quota is used up. Please try again in a few minutes.' });
    const user = userEvent.setup();
    renderStudio();
    await screen.findByRole('option', { name: 'Anglais' });
    await user.click(screen.getByRole('button', { name: /Generate quiz/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The AI service is busy');
  });
});
