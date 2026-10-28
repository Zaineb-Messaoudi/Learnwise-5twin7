import { apiRequest, apiClient } from './client';

export const coursesApi = {
    list: (params = '') => apiRequest(`/content/courses/${params}`),
    catalog: () => apiRequest('/content/courses/?available=true'),
    detail: (id) => apiRequest(`/content/courses/${id}/`),
    create: (payload) => apiRequest('/content/courses/', { method: 'POST', body: payload }),
    update: (id, payload) => apiRequest(`/content/courses/${id}/`, { method: 'PATCH', body: payload }),
    publish: (id) => apiRequest(`/content/courses/${id}/publish/`, { method: 'POST' }),

    // Advanced course management endpoints
    archive: (id) => apiRequest(`/content/courses/${id}/archive/`, { method: 'POST' }),
    stats: () => apiRequest('/content/courses/stats/'),
    versions: (id) => apiRequest(`/content/courses/${id}/versions/`),
    createVersion: (id, data) => apiRequest(`/content/courses/${id}/create_version/`, { method: 'POST', body: data }),
    rollback: (id, version_id) => apiRequest(`/content/courses/${id}/rollback/`, { method: 'POST', body: { version_id } }),
    duplicate: (id, data) => apiRequest(`/content/courses/${id}/duplicate/`, { method: 'POST', body: data }),
    export: async (id) => {
      const response = await apiClient.get(`/content/courses/${id}/export/`, { responseType: 'blob' });
      return response;
    },
    submitForReview: (id) => apiRequest(`/content/courses/${id}/submit_for_review/`, { method: 'POST' }),
    approve: (id) => apiRequest(`/content/courses/${id}/approve/`, { method: 'POST' }),
    reject: (id) => apiRequest(`/content/courses/${id}/reject/`, { method: 'POST' }),

    // Prerequisite management
    prerequisites: (id) => apiRequest(`/content/courses/${id}/prerequisites/`),
    addPrerequisite: (id, data) => apiRequest(`/content/courses/${id}/prerequisites/`, { method: 'POST', body: data }),
    removePrerequisite: (id, prereqId) => apiRequest(`/content/courses/${id}/prerequisites/${prereqId}/`, { method: 'DELETE' }),
};
