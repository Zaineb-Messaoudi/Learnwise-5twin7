import { apiRequest } from './client';
export const materialsApi = {
    list: (courseId) => apiRequest(`/content/materials/${courseId ? `?course=${encodeURIComponent(courseId)}` : ''}`),
    detail: (id) => apiRequest(`/content/materials/${id}/`),
    upload: (courseId, file, metadata = {}, onUploadProgress) => {
        const body = new FormData();
        body.append('file', file);
        body.append('kind', metadata.kind || (file.type.startsWith('audio/') ? 'audio' : 'document'));
        if (metadata.language) body.append('language', metadata.language);
        return apiRequest(`/content/courses/${encodeURIComponent(courseId)}/materials/`, { method: 'POST', body, onUploadProgress });
    },
    processingStatus: (id) => apiRequest(`/content/materials/${id}/processing/`),
    retryProcessing: (id) => apiRequest(`/content/materials/${id}/retry/`, { method: 'POST' }),
    transcription: (id) => apiRequest(`/content/materials/${id}/transcription/`),
    updateTranscription: (id, text) => apiRequest(`/content/materials/${id}/transcription/`, { method: 'PATCH', body: { text } }),
    summary: (id) => apiRequest(`/content/materials/${id}/summary/`),
    updateSummary: (id, text) => apiRequest(`/content/materials/${id}/summary/`, { method: 'PATCH', body: { text } }),
    regenerateSummary: (id) => apiRequest(`/content/materials/${id}/summary/regenerate/`, { method: 'POST' }),
};
