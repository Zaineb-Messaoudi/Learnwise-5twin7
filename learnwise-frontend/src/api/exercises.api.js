import { apiRequest } from './client';
export const exercisesApi = {
    list: (courseId) => apiRequest(`/assessment/exercises/${courseId ? `?course=${encodeURIComponent(courseId)}` : ''}`),
    detail: (id) => apiRequest(`/assessment/exercises/${id}/`),
    create: (payload) => apiRequest('/assessment/exercises/', { method: 'POST', body: payload }),
    update: (id, payload) => apiRequest(`/assessment/exercises/${id}/`, { method: 'PATCH', body: payload }),
    remove: (id) => apiRequest(`/assessment/exercises/${id}/`, { method: 'DELETE' }),
    publish: (id) => apiRequest(`/assessment/exercises/${id}/publish/`, { method: 'POST' }),
    submit: (id, answer) => apiRequest(`/assessment/exercises/${id}/submissions/`, { method: 'POST', body: { answer } }),
};
