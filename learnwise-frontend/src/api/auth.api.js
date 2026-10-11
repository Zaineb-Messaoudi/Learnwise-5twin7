import { apiRequest } from './client';

export const authApi = {
    // Authentication
    login: (payload) => apiRequest('/auth/login/', { method: 'POST', body: payload }),
    logout: (refresh) => apiRequest('/auth/logout/', { method: 'POST', body: refresh ? { refresh } : {} }),
    refresh: (refresh) => apiRequest('/auth/token/refresh/', { method: 'POST', body: { refresh } }),
    register: (payload) => apiRequest('/accounts/register/', { method: 'POST', body: payload }),
    me: () => apiRequest('/accounts/me/'),
    updateProfile: (payload) => apiRequest('/accounts/me/', { method: 'PATCH', body: payload }),
    changePassword: (payload) => apiRequest('/accounts/change-password/', { method: 'POST', body: payload }),

    // Password reset
    requestPasswordReset: (email) => apiRequest('/auth/password-reset/', { method: 'POST', body: { email } }),
    confirmPasswordReset: (payload) => apiRequest('/auth/password-reset/confirm/', { method: 'POST', body: payload }),

    // Email verification
    verifyEmail: (token) => apiRequest('/auth/verify-email/', { method: 'POST', body: { token } }),
    resendVerification: () => apiRequest('/accounts/resend-verification/', { method: 'POST' }),

    // Social auth
    socialLogin: (provider, accessToken, role, code) => apiRequest('/auth/social/', { method: 'POST', body: { provider, access_token: accessToken, code, role } }),

    // Two-factor authentication
    get2FASetup: () => apiRequest('/auth/2fa/setup/'),
    enable2FA: (payload) => apiRequest('/auth/2fa/setup/', { method: 'POST', body: payload }),
    disable2FA: (payload) => apiRequest('/auth/2fa/disable/', { method: 'POST', body: payload }),

    // Email change
    requestEmailChange: (newEmail) => apiRequest('/auth/email-change/', { method: 'POST', body: { new_email: newEmail } }),
    confirmEmailChange: (token) => apiRequest('/auth/email-change/confirm/', { method: 'POST', body: { token } }),

    // Session management
    listSessions: () => apiRequest('/auth/sessions/'),
    revokeSession: (sessionId) => apiRequest(`/auth/sessions/${sessionId}/revoke/`, { method: 'POST' }),
    revokeAllSessions: () => apiRequest('/auth/sessions/revoke-all/', { method: 'POST' }),

    // Avatar
    uploadAvatar: (file) => apiRequest('/accounts/avatar/', { method: 'POST', body: file, isFormData: true }),
    removeAvatar: () => apiRequest('/accounts/avatar/remove/', { method: 'DELETE' }),

    // Security events
    getSecurityEvents: () => apiRequest('/auth/security-events/'),

    // Activity logs
    getActivityLogs: () => apiRequest('/auth/activity-logs/'),

    // Terms & consent
    getTerms: () => apiRequest('/accounts/terms/'),
    acceptTerms: (payload) => apiRequest('/accounts/terms/accept/', { method: 'POST', body: payload }),
    acceptPrivacy: () => apiRequest('/accounts/privacy/accept/', { method: 'POST' }),

    // Data export
    getDataExports: () => apiRequest('/auth/data-export/'),
    requestDataExport: () => apiRequest('/auth/data-export/', { method: 'POST' }),

    // Account deletion
    getDeletionRequest: () => apiRequest('/auth/deletion-request/'),
    requestAccountDeletion: (payload) => apiRequest('/auth/deletion-request/', { method: 'POST', body: payload }),
    confirmAccountDeletion: (payload) => apiRequest('/auth/deletion/confirm/', { method: 'POST', body: payload }),
    cancelAccountDeletion: () => apiRequest('/auth/deletion/cancel/', { method: 'POST' }),

    // Admin endpoints
    adminListUsers: (params = {}) => apiRequest('/accounts/admin/users/', { params }),
    adminGetUser: (id) => apiRequest(`/accounts/admin/users/${id}/`),
    adminUpdateUser: (id, payload) => apiRequest(`/accounts/admin/users/${id}/`, { method: 'PATCH', body: payload }),
    adminActivateUser: (id) => apiRequest(`/accounts/admin/users/${id}/activate/`, { method: 'POST' }),
    adminDeactivateUser: (id) => apiRequest(`/accounts/admin/users/${id}/deactivate/`, { method: 'POST' }),
    adminMakeAdmin: (id) => apiRequest(`/accounts/admin/users/${id}/make_admin/`, { method: 'POST' }),
    adminRemoveAdmin: (id) => apiRequest(`/accounts/admin/users/${id}/remove_admin/`, { method: 'POST' }),
    adminLockUser: (id) => apiRequest(`/accounts/admin/users/${id}/lock/`, { method: 'POST' }),
    adminUnlockUser: (id) => apiRequest(`/accounts/admin/users/${id}/unlock/`, { method: 'POST' }),
    adminGetStats: () => apiRequest('/accounts/admin/users/stats/'),
};