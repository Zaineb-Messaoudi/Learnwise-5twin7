import { apiRequest } from './client';
export const coursesApi = {
    list: (params = '') => apiRequest(`/content/courses/${params}`),
    catalog: () => apiRequest('/content/courses/?available=true'),
    detail: (id) => apiRequest(`/content/courses/${id}/`),
    create: (payload) => apiRequest('/content/courses/', { method: 'POST', body: payload }),
    update: (id, payload) => apiRequest(`/content/courses/${id}/`, { method: 'PATCH', body: payload }),
    publish: (id) => apiRequest(`/content/courses/${id}/publish/`, { method: 'POST' }),
};
