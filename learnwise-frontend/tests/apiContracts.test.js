jest.mock('../src/api/client', () => ({ apiRequest: jest.fn(() => Promise.resolve({ ok: true })) }));

import { apiRequest } from '../src/api/client';
import { coursesApi } from '../src/api/courses.api';
import { materialsApi } from '../src/api/materials.api';
import { assistantApi } from '../src/api/assistant.api';
import { quizzesApi } from '../src/api/quizzes.api';
import { exercisesApi } from '../src/api/exercises.api';
import { analyticsApi } from '../src/api/analytics.api';
import { authApi } from '../src/api/auth.api';

describe('frontend API module ownership and contracts', () => {
  beforeEach(() => apiRequest.mockClear());

  test('course/material APIs stay in content-management namespace and upload multipart data', () => {
    const course = { title: 'Neural networks', description: 'Course overview', level: 'intermediate', language: 'en' };
    coursesApi.create(course);
    expect(apiRequest).toHaveBeenLastCalledWith('/content/courses/', { method: 'POST', body: course });
    const file = new File(['pdf'], 'notes.pdf', { type: 'application/pdf' });
    materialsApi.upload('course-1', file, { kind: 'document' });
    const [path, options] = apiRequest.mock.calls.at(-1);
    expect(path).toBe('/content/courses/course-1/materials/');
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get('file')).toBe(file);
  });

  test('assistant voice and conversation operations stay in the assistant namespace', () => {
    assistantApi.ask('session-1', { content: 'Explain gradients' });
    expect(apiRequest).toHaveBeenLastCalledWith('/assistant/sessions/session-1/messages/', { method: 'POST', body: { content: 'Explain gradients' } });
    expect(assistantApi.socketPath('session-1')).toBe('/ws/assistant/sessions/session-1/');
  });

  test('assessment attempts keep answer saving and submission separate', () => {
    quizzesApi.saveAttempt('quiz-1', 'attempt-1', { q1: 'c1' });
    expect(apiRequest).toHaveBeenLastCalledWith('/assessment/quizzes/quiz-1/attempts/attempt-1/', { method: 'PATCH', body: { answers: { q1: 'c1' } } });
    quizzesApi.submit('quiz-1', 'attempt-1', { q1: 'c1' });
    expect(apiRequest).toHaveBeenLastCalledWith('/assessment/quizzes/quiz-1/attempts/attempt-1/submit/', { method: 'POST', body: { answers: { q1: 'c1' } } });
    exercisesApi.publish('exercise-1');
    expect(apiRequest).toHaveBeenLastCalledWith('/assessment/exercises/exercise-1/publish/', { method: 'POST' });
  });

  test('analytics and account endpoints use their domain-owned routes', () => {
    analyticsApi.learningPaths();
    expect(apiRequest).toHaveBeenLastCalledWith('/analytics/learning-paths/');
    analyticsApi.startLearningSession('course-1');
    expect(apiRequest).toHaveBeenLastCalledWith('/analytics/learning-sessions/', { method: 'POST', body: { course_id: 'course-1' } });
    analyticsApi.recordActivity({ session_id: 'session-1', course_id: 'course-1', activity_type: 'lesson_started' });
    expect(apiRequest).toHaveBeenLastCalledWith('/analytics/learning-activities/', { method: 'POST', body: { session_id: 'session-1', course_id: 'course-1', activity_type: 'lesson_started' } });
    coursesApi.catalog();
    expect(apiRequest).toHaveBeenLastCalledWith('/content/courses/?available=true');
    authApi.register({ email: 'student@example.test', password: 'secure-pass', role: 'student' });
    expect(apiRequest).toHaveBeenLastCalledWith('/accounts/register/', { method: 'POST', body: { email: 'student@example.test', password: 'secure-pass', role: 'student' } });
    authApi.requestPasswordReset('student@example.test');
    expect(apiRequest).toHaveBeenLastCalledWith('/auth/password-reset/', { method: 'POST', body: { email: 'student@example.test' } });
    authApi.confirmPasswordReset({ token: 'reset-token', password: 'new-secure-pass' });
    expect(apiRequest).toHaveBeenLastCalledWith('/auth/password-reset/confirm/', { method: 'POST', body: { token: 'reset-token', password: 'new-secure-pass' } });
    authApi.me();
    expect(apiRequest).toHaveBeenLastCalledWith('/accounts/me/');
  });
});
