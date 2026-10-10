import { apiRequest } from './client';
export const assistantApi = {
    sessions: () => apiRequest('/assistant/sessions/'),
    createSession: (payload = {}) => apiRequest('/assistant/sessions/', { method: 'POST', body: payload }),
    session: (sessionId) => apiRequest(`/assistant/sessions/${sessionId}/`),
    messages: (sessionId) => apiRequest(`/assistant/sessions/${sessionId}/messages/`),
    ask: (sessionId, payload) => apiRequest(`/assistant/sessions/${sessionId}/messages/`, { method: 'POST', body: typeof payload === 'string' ? { content: payload } : payload }),
    uploadVoiceQuestion: (sessionId, audio, metadata = {}) => {
        const body = new FormData();
        body.append('audio', audio, metadata.filename || 'voice-question.webm');
        if (metadata.language) body.append('language', metadata.language);
        return apiRequest(`/assistant/sessions/${sessionId}/voice-questions/`, { method: 'POST', body });
    },
    voiceQuestion: (questionId) => apiRequest(`/assistant/voice-questions/${questionId}/`),
    updateVoiceTranscript: (questionId, transcript) => apiRequest(`/assistant/voice-questions/${questionId}/`, { method: 'PATCH', body: { transcript } }),
    generateIllustration: (sessionId, prompt, style = 'educational') => apiRequest(`/assistant/sessions/${sessionId}/illustrations/`, { method: 'POST', body: { prompt, style } }),
    illustration: (illustrationId) => apiRequest(`/assistant/illustrations/${illustrationId}/`),
    socketPath: (sessionId) => `/ws/assistant/sessions/${encodeURIComponent(sessionId)}/`,
};
