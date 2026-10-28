import { apiRequest } from './client';

export const assistantApi = {
    sessions: () => apiRequest('/ai/sessions/'),
    createSession: (payload = {}) => apiRequest('/ai/sessions/', { method: 'POST', body: payload }),
    session: (sessionId) => apiRequest(`/ai/sessions/${sessionId}/`),
    messages: (sessionId) => apiRequest(`/ai/sessions/${sessionId}/messages/`),
    ask: (sessionId, payload) => apiRequest(`/ai/sessions/${sessionId}/messages/`, { method: 'POST', body: typeof payload === 'string' ? { content: payload } : payload }),
    uploadVoiceQuestion: (sessionId, audio, metadata = {}) => {
        const body = new FormData();
        body.append('audio', audio, metadata.filename || 'voice-question.webm');
        if (metadata.language) body.append('language', metadata.language);
        body.append('session', sessionId);
        return apiRequest('/ai/voice-questions/', { method: 'POST', body });
    },
    voiceQuestion: (questionId) => apiRequest(`/assistant/voice-questions/${questionId}/`),
    updateVoiceTranscript: (questionId, transcript) => apiRequest(`/assistant/voice-questions/${questionId}/`, { method: 'PATCH', body: { transcript } }),
    generateIllustration: (messageId, prompt, style = 'educational') => apiRequest(`/assistant/messages/${messageId}/illustrations/`, { method: 'POST', body: { prompt, style } }),
    illustration: (illustrationId) => apiRequest(`/assistant/illustrations/${illustrationId}/`),

    socketPath: (sessionId) => `/ws/assistant/sessions/${encodeURIComponent(sessionId)}/`,
};
