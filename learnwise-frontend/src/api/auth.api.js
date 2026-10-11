import { apiRequest } from './client';

export const authApi = {
    login: (payload) => apiRequest('/auth/login/', { method: 'POST', body: payload }),
    register: (payload) => apiRequest('/accounts/register/', { method: 'POST', body: payload }),
    logout: (refresh) => apiRequest('/auth/logout/', { method: 'POST', body: refresh ? { refresh } : {} }),
    refresh: (refresh) => apiRequest('/auth/token/refresh/', { method: 'POST', body: { refresh } }),
    me: () => apiRequest('/accounts/me/'),
    updateProfile: (payload) => apiRequest('/accounts/me/', { method: 'PATCH', body: payload }),
    changePassword: (payload) => apiRequest('/accounts/change-password/', { method: 'POST', body: payload }),
    requestPasswordReset: (email) => apiRequest('/auth/password-reset/', { method: 'POST', body: { email } }),
    confirmPasswordReset: (payload) => apiRequest('/auth/password-reset/confirm/', { method: 'POST', body: payload }),
    verifyEmail: (token) => apiRequest('/auth/verify-email/', { method: 'POST', body: { token } }),
    resendVerification: () => apiRequest('/accounts/resend-verification/', { method: 'POST' }),
    socialLogin: (provider, accessToken, role) => apiRequest('/auth/social/', { method: 'POST', body: { provider, access_token: accessToken, role } }),
    // Admin endpoints
    adminListUsers: (params = {}) => apiRequest('/admin/users/', { params }),
    adminGetUser: (id) => apiRequest(`/admin/users/${id}/`),
    adminUpdateUser: (id, payload) => apiRequest(`/admin/users/${id}/`, { method: 'PATCH', body: payload }),
    adminActivateUser: (id) => apiRequest(`/admin/users/${id}/activate/`, { method: 'POST' }),
    adminDeactivateUser: (id) => apiRequest(`/admin/users/${id}/deactivate/`, { method: 'POST' }),
    adminMakeAdmin: (id) => apiRequest(`/admin/users/${id}/make_admin/`, { method: 'POST' }),
    adminRemoveAdmin: (id) => apiRequest(`/admin/users/${id}/remove_admin/`, { method: 'POST' }),
    adminGetStats: () => apiRequest('/admin/users/stats/'),
};