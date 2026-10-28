import { apiRequest, apiClient } from './client';
export const materialsApi = {
    list: (courseId) => apiRequest(`/content/materials/${courseId ? `?course=${encodeURIComponent(courseId)}` : ''}`),
    detail: (id) => apiRequest(`/content/materials/${id}/`),
    upload: (courseId, file, metadata = {}, onUploadProgress) => {
        const body = new FormData();
        body.append('file', file);
        body.append('material_type', metadata.material_type || metadata.kind || (file.type.startsWith('audio/') ? 'audio' : 'document'));
        body.append('title', metadata.title || file.name);
        if (metadata.language) body.append('language', metadata.language);
        body.append('course', courseId);
        return apiRequest(`/content/materials/`, { method: 'POST', body, onUploadProgress });
    },
    processingStatus: (id) => apiRequest(`/content/materials/${id}/processing/`),
    retryProcessing: (id) => apiRequest(`/content/materials/${id}/retry/`, { method: 'POST' }),
    transcription: (id) => apiRequest(`/content/materials/${id}/transcription/`),
    updateTranscription: (id, text) => apiRequest(`/content/materials/${id}/transcription/`, { method: 'PATCH', body: { content: text } }),
    summary: (id) => apiRequest(`/content/materials/${id}/summary/`),
    updateSummary: (id, text) => apiRequest(`/content/materials/${id}/summary/`, { method: 'PATCH', body: { content: text } }),
    regenerateSummary: (id) => apiRequest(`/content/materials/${id}/regenerate_summary/`, { method: 'POST' }),

    // New thumbnail and chapter endpoints
    generateThumbnail: (id) => apiRequest(`/content/materials/${id}/generate_thumbnail/`, { method: 'POST' }),

    // Chapter management
    chapters: (courseId) => apiRequest(`/content/chapters/?course=${encodeURIComponent(courseId)}`),
    createChapter: (data) => apiRequest(`/content/chapters/`, { method: 'POST', body: data }),
    updateChapter: (id, data) => apiRequest(`/content/chapters/${id}/`, { method: 'PATCH', body: data }),
    deleteChapter: (id) => apiRequest(`/content/chapters/${id}/`, { method: 'DELETE' }),

    // Download a material (also marks it as completed for the student, used for quiz gating)
    download: async (id) => {
      const response = await apiClient.get(`/content/materials/${id}/download/`, { responseType: 'blob' });
      return response;
    },

    // Lesson completions for quiz gating
    listCompletions: () => apiRequest('/content/lesson-completions/'),
    complete: (id) => apiRequest(`/content/materials/${id}/complete/`, { method: 'POST' }),
};
