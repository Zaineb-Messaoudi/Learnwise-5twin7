import { apiRequest } from './client';

export const notebooksApi = {
    list: () => apiRequest('/notebooks/'),
    create: (payload) => apiRequest('/notebooks/', { method: 'POST', body: payload }),
    detail: (id) => apiRequest(`/notebooks/${id}/`),
    update: (id, payload) => apiRequest(`/notebooks/${id}/`, { method: 'PATCH', body: payload }),
    delete: (id) => apiRequest(`/notebooks/${id}/`, { method: 'DELETE' }),
    sources: (notebookId) => apiRequest(`/notebooks/${notebookId}/sources/`),
    addSource: (notebookId, payload) => apiRequest(`/notebooks/${notebookId}/sources/`, { method: 'POST', body: payload }),
    removeSource: (notebookId, sourceId) => apiRequest(`/notebooks/${notebookId}/sources/${sourceId}/`, { method: 'DELETE' }),
    sourceDetail: (notebookId, sourceId) => apiRequest(`/notebooks/${notebookId}/sources/${sourceId}/`),
    chat: (notebookId, payload) => apiRequest(`/notebooks/${notebookId}/chat/`, { method: 'POST', body: payload }),
    generateGuide: (notebookId, guideType, options = {}) => apiRequest(`/notebooks/${notebookId}/guides/`, { method: 'POST', body: { type: guideType, ...options } }),
    getGuide: (notebookId, guideId) => apiRequest(`/notebooks/${notebookId}/guides/${guideId}/`),
    notes: (notebookId) => apiRequest(`/notebooks/${notebookId}/notes/`),
    createNote: (notebookId, payload) => apiRequest(`/notebooks/${notebookId}/notes/`, { method: 'POST', body: payload }),
    updateNote: (notebookId, noteId, payload) => apiRequest(`/notebooks/${notebookId}/notes/${noteId}/`, { method: 'PATCH', body: payload }),
    deleteNote: (notebookId, noteId) => apiRequest(`/notebooks/${notebookId}/notes/${noteId}/`, { method: 'DELETE' }),
    suggestedNotes: (notebookId, sourceIds) => apiRequest(`/notebooks/${notebookId}/suggested-notes/`, { method: 'POST', body: { source_ids: sourceIds } }),
    keyPoints: (notebookId, sourceIds) => apiRequest(`/notebooks/${notebookId}/key-points/`, { method: 'POST', body: { source_ids: sourceIds } }),
};