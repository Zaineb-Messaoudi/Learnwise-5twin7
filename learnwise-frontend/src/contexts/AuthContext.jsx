import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { authApi } from '../api/auth.api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => {
        try {
            const raw = window.localStorage.getItem('learnwise:user');
            return raw ? JSON.parse(raw) : null;
        } catch {
            window.localStorage.removeItem('learnwise:user');
            return null;
        }
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const clearSession = () => {
        setUser(null);
        ['learnwise:user', 'learnwise-role', 'learnwise:access-token', 'learnwise:refresh-token'].forEach(key => window.localStorage.removeItem(key));
    };

    const login = (next, tokens = {}) => {
        setUser(next);
        window.localStorage.setItem('learnwise:user', JSON.stringify(next));
        window.localStorage.setItem('learnwise-role', next.role);
        if (tokens.access) window.localStorage.setItem('learnwise:access-token', tokens.access);
        else window.localStorage.removeItem('learnwise:access-token');
        if (tokens.refresh) window.localStorage.setItem('learnwise:refresh-token', tokens.refresh);
        else window.localStorage.removeItem('learnwise:refresh-token');
    };

    const updateUser = next => {
        setUser(next);
        window.localStorage.setItem('learnwise:user', JSON.stringify(next));
        window.localStorage.setItem('learnwise-role', next.role);
    };

    const logout = async () => {
        const refresh = window.localStorage.getItem('learnwise:refresh-token');
        if (refresh) {
            try {
                await authApi.logout(refresh);
            } catch {
                // Ignore logout errors
            }
        }
        clearSession();
    };

    const changePassword = async (payload) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.changePassword(payload);
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to change password.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const updateProfile = async (payload) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.updateProfile(payload);
            updateUser(response);
            return { success: true, user: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to update profile.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const requestPasswordReset = async (email) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.requestPasswordReset(email);
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to send reset email.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const confirmPasswordReset = async (token, password) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.confirmPasswordReset({ token, password });
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to reset password.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const verifyEmail = async (token) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.verifyEmail(token);
            if (response?.user && response?.access && response?.refresh) {
                login(response.user, { access: response.access, refresh: response.refresh });
            }
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to verify email.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const resendVerification = async () => {
        setLoading(true);
        setError(null);
        try {
            await authApi.resendVerification();
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to send verification email.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const socialLogin = async (provider, accessToken, role = 'etudiant', code = null) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.socialLogin(provider, accessToken, role, code);
            if (response?.user && response?.access && response?.refresh) {
                login(response.user, { access: response.access, refresh: response.refresh });
            }
            return { success: true, isNewUser: response?.is_new_user };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || `Failed to sign in with ${provider}.`;
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // 2FA
    const get2FASetup = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.get2FASetup();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load 2FA setup.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const enable2FA = async (payload) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.enable2FA(payload);
            return { success: true, backupCodes: response.backup_codes };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to enable 2FA.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const disable2FA = async (payload) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.disable2FA(payload);
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to disable 2FA.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // Email change
    const requestEmailChange = async (newEmail) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.requestEmailChange(newEmail);
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to request email change.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const confirmEmailChange = async (token) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.confirmEmailChange(token);
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to confirm email change.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // Session management
    const listSessions = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.listSessions();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load sessions.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const revokeSession = async (sessionId) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.revokeSession(sessionId);
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to revoke session.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const revokeAllSessions = async () => {
        setLoading(true);
        setError(null);
        try {
            await authApi.revokeAllSessions();
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to revoke sessions.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // Avatar
    const uploadAvatar = async (file) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.uploadAvatar(file);
            return { success: true, avatar_url: response.avatar_url };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to upload avatar.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const removeAvatar = async () => {
        setLoading(true);
        setError(null);
        try {
            await authApi.removeAvatar();
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to remove avatar.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // Security events
    const getSecurityEvents = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.getSecurityEvents();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load security events.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // Activity logs
    const getActivityLogs = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.getActivityLogs();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load activity logs.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // Terms & consent
    const getTerms = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.getTerms();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load terms.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const acceptTerms = async (payload) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.acceptTerms(payload);
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to accept terms.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const acceptPrivacy = async () => {
        setLoading(true);
        setError(null);
        try {
            await authApi.acceptPrivacy();
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to accept privacy policy.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // Data export
    const getDataExports = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.getDataExports();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load data exports.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const requestDataExport = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.requestDataExport();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to request data export.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    // Account deletion
    const getDeletionRequest = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.getDeletionRequest();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load deletion request.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const requestAccountDeletion = async (payload) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.requestAccountDeletion(payload);
            return { success: true, message: response.detail };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to request account deletion.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const confirmAccountDeletion = async (payload) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.confirmAccountDeletion(payload);
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to confirm account deletion.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const cancelAccountDeletion = async () => {
        setLoading(true);
        setError(null);
        try {
            await authApi.cancelAccountDeletion();
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to cancel account deletion.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const handleExpired = () => clearSession();
        window.addEventListener('learnwise:auth-expired', handleExpired);
        return () => window.removeEventListener('learnwise:auth-expired', handleExpired);
    }, []);

    const value = useMemo(() => ({
        user,
        login,
        updateUser,
        logout,
        changePassword,
        updateProfile,
        requestPasswordReset,
        confirmPasswordReset,
        verifyEmail,
        resendVerification,
        socialLogin,
        get2FASetup,
        enable2FA,
        disable2FA,
        requestEmailChange,
        confirmEmailChange,
        listSessions,
        revokeSession,
        revokeAllSessions,
        uploadAvatar,
        removeAvatar,
        getSecurityEvents,
        getActivityLogs,
        getTerms,
        acceptTerms,
        acceptPrivacy,
        getDataExports,
        requestDataExport,
        getDeletionRequest,
        requestAccountDeletion,
        confirmAccountDeletion,
        cancelAccountDeletion,
        isAuthenticated: Boolean(user),
        loading,
        error,
        clearError: () => setError(null),
    }), [user, loading, error]);

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const value = useContext(AuthContext);
    if (!value)
        throw new Error('useAuth must be used inside AuthProvider');
    return value;
}