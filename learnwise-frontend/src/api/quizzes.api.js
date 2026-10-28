import { apiRequest } from './client';
export const quizzesApi = {
    list: (courseId) => apiRequest(`/assessment/quizzes/${courseId ? `?course=${encodeURIComponent(courseId)}` : ''}`),
    detail: (id) => apiRequest(`/assessment/quizzes/${id}/`),
    create: (payload) => apiRequest('/assessment/quizzes/', { method: 'POST', body: payload }),
    update: (id, payload) => apiRequest(`/assessment/quizzes/${id}/`, { method: 'PATCH', body: payload }),
    generate: (payload) => apiRequest('/assessment/generations/', { method: 'POST', body: payload }),
    generation: (id) => apiRequest(`/assessment/generations/${id}/`),
    publish: (id) => apiRequest(`/assessment/quizzes/${id}/publish/`, { method: 'POST' }),
    attempts: (id) => apiRequest(`/assessment/quizzes/${id}/attempts/`),
    startAttempt: (id) => apiRequest(`/assessment/quizzes/${id}/attempts/`, { method: 'POST', body: { answers: {} } }),
    saveAttempt: (id, attemptId, answers) => apiRequest(`/assessment/quizzes/${id}/attempts/${attemptId}/submit/`, { method: 'POST', body: { answers } }),
    submit: (id, attemptId, answers) => apiRequest(`/assessment/quizzes/${id}/attempts/${attemptId}/submit/`, { method: 'POST', body: { answers } }),
    result: (id, attemptId) => apiRequest(`/assessment/quizzes/${id}/attempts/${attemptId}/evaluation/`),
};
