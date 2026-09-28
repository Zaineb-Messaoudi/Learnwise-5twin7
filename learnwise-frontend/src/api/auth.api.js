import { apiRequest } from './client';
export const authApi = {
    login: (payload) => apiRequest('/auth/token/', { method: 'POST', body: payload }),
    register: (payload) => apiRequest('/accounts/register/', { method: 'POST', body: payload }),
    requestPasswordReset: (email) => apiRequest('/auth/password-reset/', { method: 'POST', body: { email } }),
    confirmPasswordReset: (payload) => apiRequest('/auth/password-reset/confirm/', { method: 'POST', body: payload }),
    refresh: (refresh) => apiRequest('/auth/token/refresh/', { method: 'POST', body: { refresh } }),
    logout: (refresh) => apiRequest('/auth/logout/', { method: 'POST', body: refresh ? { refresh } : {} }),
    me: () => apiRequest('/accounts/me/'),
    updateProfile: (payload) => apiRequest('/accounts/me/', { method: 'PATCH', body: payload }),
};
