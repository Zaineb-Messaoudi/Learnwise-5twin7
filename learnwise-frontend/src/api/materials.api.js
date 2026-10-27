import { apiRequest } from './client';
export const materialsApi = {
    list: (courseId) => apiRequest(`/content/materials/${courseId ? `?course=${encodeURIComponent(courseId)}` : ''}`),
    detail: (id) => apiRequest(`/content/materials/${id}/`),
    upload: (courseId, file, metadata = {}, onUploadProgress) => {
        const body = new FormData();
        body.append('file', file);
        body.append('kind', metadata.kind || (file.type.startsWith('audio/') ? 'audio' : 'document'));
        if (metadata.language) body.append('language', metadata.language);
        body.append('course', courseId);  // Add course to FormData
        return apiRequest(`/content/materials/`, { method: 'POST', body, onUploadProgress });
    },
    processingStatus: (id) => apiRequest(`/content/materials/${id}/processing/`),
    retryProcessing: (id) => apiRequest(`/content/materials/${id}/retry/`, { method: 'POST' }),
    transcription: (id) => apiRequest(`/content/materials/${id}/transcription/`),
    updateTranscription: (id, text) => apiRequest(`/content/materials/${id}/transcription/`, { method: 'PATCH', body: { text } }),
    summary: (id) => apiRequest(`/content/materials/${id}/summary/`),
    updateSummary: (id, text) => apiRequest(`/content/materials/${id}/summary/`, { method: 'PATCH', body: { text } }),
    regenerateSummary: (id) => apiRequest(`/content/materials/${id}/summary/regenerate/`, { method: 'POST' }),

    // New thumbnail and chapter endpoints
    generateThumbnail: (id) => apiRequest(`/content/materials/${id}/generate_thumbnail/`, { method: 'POST' }),

    // Chapter management
    chapters: (courseId) => apiRequest(`/content/chapters/?course=${encodeURIComponent(courseId)}`),
    createChapter: (data) => apiRequest(`/content/chapters/`, { method: 'POST', body: data }),
    updateChapter: (id, data) => apiRequest(`/content/chapters/${id}/`, { method: 'PATCH', body: data }),
    deleteChapter: (id) => apiRequest(`/content/chapters/${id}/`, { method: 'DELETE' }),
};
