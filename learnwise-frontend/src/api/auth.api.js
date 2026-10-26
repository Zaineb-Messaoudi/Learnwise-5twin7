import { apiClient, apiRequest } from './client';

export const authApi = {
    // Authentication
    // payload: { email, password, totp_token?, backup_code?, remember_me? }
    login: (payload) => apiRequest('/auth/login/', { method: 'POST', body: payload }),
    logout: (refresh) => apiRequest('/auth/logout/', { method: 'POST', body: refresh ? { refresh } : {} }),
    refresh: (refresh) => apiRequest('/auth/token/refresh/', { method: 'POST', body: { refresh } }),
    // payload: { email, password, confirm_password, first_name, last_name, role: 'etudiant'|'professeur', terms_version? }
    register: (payload) => apiRequest('/accounts/register/', { method: 'POST', body: payload }),
    me: () => apiRequest('/accounts/me/'),
    updateProfile: (payload) => apiRequest('/accounts/me/', { method: 'PATCH', body: payload }),
    // current_password is omitted for accounts that signed up with Google/Facebook (no password yet)
    changePassword: (payload) => apiRequest('/accounts/change-password/', { method: 'POST', body: payload }),

    // Password reset
    requestPasswordReset: (email) => apiRequest('/auth/password-reset/', { method: 'POST', body: { email } }),
    // The backend also requires confirm_password; it defaults to the password so single-field callers keep working.
    confirmPasswordReset: ({ token, password, confirm_password }) => apiRequest('/auth/password-reset/confirm/', { method: 'POST', body: { token, password, confirm_password: confirm_password ?? password } }),

    // Email verification
    verifyEmail: (token) => apiRequest('/auth/verify-email/', { method: 'POST', body: { token } }),
    verifyCode: (code) => apiRequest('/auth/verify-code/', { method: 'POST', body: { code } }),
    resendVerification: () => apiRequest('/accounts/resend-verification/', { method: 'POST' }),
    stepUp: (password) => apiRequest('/auth/step-up/', { method: 'POST', body: { password } }),
    // For people who cannot sign in yet because the address is not verified
    resendVerificationPublic: (email) => apiRequest('/auth/resend-verification/', { method: 'POST', body: { email } }),

    // Social auth
    socialLogin: (provider, accessToken, role, code) => {
      const body = { provider };
      if (role) body.role = role;
      if (accessToken) body.access_token = accessToken;
      if (code) body.code = code;
      return apiRequest('/auth/social/', { method: 'POST', body });
    },
    selectRole: (role) => apiRequest('/auth/select-role/', { method: 'POST', body: { role } }),

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

    // Avatar (the backend reads the multipart field `avatar`)
    uploadAvatar: (file) => {
      const formData = new FormData();
      formData.append('avatar', file);
      return apiRequest('/accounts/avatar/', { method: 'POST', body: formData });
    },
    removeAvatar: () => apiRequest('/accounts/avatar/remove/', { method: 'DELETE' }),

    // Face recognition. The 128-number descriptor is what actually gets matched at
    // sign-in; `enrollmentImage` (the captured/uploaded photo, as a base64 data: URL
    // or a File/Blob) is stored only as a reference image, never used for matching.
    // `password` is required by the backend for accounts that already have one
    // (re-authentication before a face can be enrolled or replaced); it is omitted
    // for Google/Facebook accounts, which have no usable password.
    registerFace: async (descriptor, qualityScore, enrollmentImage, password) => {
      const formData = new FormData();
      formData.append('descriptor', JSON.stringify(descriptor));
      formData.append('quality_score', String(Math.min(1, Math.max(0, Number(qualityScore) || 0))));
      if (password) formData.append('password', password);
      if (enrollmentImage) {
        const imageBlob = typeof enrollmentImage === 'string' && enrollmentImage.startsWith('data:')
          ? await (await fetch(enrollmentImage)).blob()
          : enrollmentImage;
        formData.append('enrollment_image', imageBlob, 'face-enrollment.png');
      }
      return apiRequest('/auth/face/register/', { method: 'POST', body: formData });
    },
    verifyFace: (descriptor) => apiRequest('/auth/face/verify/', { method: 'POST', body: { descriptor } }),
    getFaceProfile: () => apiRequest('/accounts/face/profile/'),
    deleteFaceProfile: () => apiRequest('/accounts/face/profile/', { method: 'DELETE' }),

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
    // The file is only served to its owner, so it must be fetched with the auth header and saved as a blob
    downloadDataExport: async (exportId) => {
      const response = await apiClient.get(`/auth/data-export/${exportId}/download/`, { responseType: 'blob' });
      return response.data;
    },

    // Account deletion
    getDeletionRequest: () => apiRequest('/auth/deletion-request/'),
    requestAccountDeletion: (payload) => apiRequest('/auth/deletion-request/', { method: 'POST', body: payload }),
    confirmAccountDeletion: (payload) => apiRequest('/auth/deletion/confirm/', { method: 'POST', body: payload }),
    cancelAccountDeletion: () => apiRequest('/auth/deletion/cancel/', { method: 'POST' }),

    // Admin endpoints
    adminListUsers: (params = {}) => apiRequest('/accounts/admin/users/', { params }),
    adminGetUser: (id) => apiRequest(`/accounts/admin/users/${id}/`),
    adminCreateUser: (payload) => apiRequest('/accounts/admin/users/', { method: 'POST', body: payload }),
    adminUpdateUser: (id, payload) => apiRequest(`/accounts/admin/users/${id}/`, { method: 'PATCH', body: payload }),
    adminDeleteUser: (id) => apiRequest(`/accounts/admin/users/${id}/`, { method: 'DELETE' }),
    adminActivateUser: (id) => apiRequest(`/accounts/admin/users/${id}/activate/`, { method: 'POST' }),
    adminDeactivateUser: (id) => apiRequest(`/accounts/admin/users/${id}/deactivate/`, { method: 'POST' }),
    adminMakeAdmin: (id) => apiRequest(`/accounts/admin/users/${id}/make_admin/`, { method: 'POST' }),
    adminRemoveAdmin: (id) => apiRequest(`/accounts/admin/users/${id}/remove_admin/`, { method: 'POST' }),
    adminLockUser: (id) => apiRequest(`/accounts/admin/users/${id}/lock/`, { method: 'POST' }),
    adminUnlockUser: (id) => apiRequest(`/accounts/admin/users/${id}/unlock/`, { method: 'POST' }),
    adminGetStats: () => apiRequest('/accounts/admin/users/stats/'),
};
