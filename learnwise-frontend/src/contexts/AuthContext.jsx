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
    // Step-up re-authentication: a face-authenticated session (weaker, no liveness)
    // cannot perform sensitive operations until the user re-authenticates with a password.
    const [stepUpRequired, setStepUpRequired] = useState(false);
    const [stepUpError, setStepUpError] = useState(null);

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

    const getUser = async () => {
        try {
            const response = await authApi.me();
            if (response) {
                setUser(response);
                window.localStorage.setItem('learnwise:user', JSON.stringify(response));
                window.localStorage.setItem('learnwise-role', response.role);
                return { success: true, data: response };
            }
            return { success: false, error: 'No user data returned' };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to fetch user profile.';
            return { success: false, error: msg };
        }
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
            const stepUpMsg = handleStepUpError(cause);
            if (stepUpMsg) {
                return { success: false, error: stepUpMsg, requiresStepUp: true };
            }
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
            return { 
                success: true, 
                isNewUser: response?.is_new_user,
                needsProfileCompletion: response?.needs_profile_completion,
                user: response?.user,
                access: response?.access,
                refresh: response?.refresh
            };
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

    const get2FAStatus = async () => {
        setLoading(true);
        setError(null);
        try {
            // Use two_factor_enabled from /me/ instead of calling /auth/2fa/setup/
            // which generates a TOTP secret and returns 400 when 2FA is already on
            const response = await getUser();
            if (response.success) {
                return { success: true, data: { two_factor_enabled: response.data?.two_factor_enabled } };
            }
            return { success: false, error: response.error || 'Failed to load 2FA status.' };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load 2FA status.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const getUserSessions = async () => {
        return listSessions();
    };

    // Social accounts
    const getSocialAccounts = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.getSocialAccounts();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load social accounts.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const unlinkSocialAccount = async (provider) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.unlinkSocialAccount(provider);
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || `Failed to unlink ${provider}.`;
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
            const stepUpMsg = handleStepUpError(cause);
            if (stepUpMsg) {
                return { success: false, error: stepUpMsg, requiresStepUp: true };
            }
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
            const stepUpMsg = handleStepUpError(cause);
            if (stepUpMsg) {
                return { success: false, error: stepUpMsg, requiresStepUp: true };
            }
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
            const stepUpMsg = handleStepUpError(cause);
            if (stepUpMsg) {
                return { success: false, error: stepUpMsg, requiresStepUp: true };
            }
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

    // Face recognition
    const registerFace = async (descriptor, qualityScore, enrollmentImage, password) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.registerFace(descriptor, qualityScore, enrollmentImage, password);
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to register face.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const verifyFace = async (descriptor) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.verifyFace(descriptor);
            if (response?.user && response?.access && response?.refresh) {
                login(response.user, { access: response.access, refresh: response.refresh });
            }
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Face verification failed.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const getFaceProfile = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.getFaceProfile();
            return { success: true, data: response };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to load face profile.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const deleteFaceProfile = async () => {
        setLoading(true);
        setError(null);
        try {
            await authApi.deleteFaceProfile();
            return { success: true };
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Failed to delete face profile.';
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
            const stepUpMsg = handleStepUpError(cause);
            if (stepUpMsg) {
                return { success: false, error: stepUpMsg, requiresStepUp: true };
            }
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
            const stepUpMsg = handleStepUpError(cause);
            if (stepUpMsg) {
                return { success: false, error: stepUpMsg, requiresStepUp: true };
            }
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

    // Detect a step-up-required error (403 with requires_step_up) from a sensitive
    // operation performed with a face-authenticated session.
    const handleStepUpError = (cause) => {
        if (cause?.response?.data?.requires_step_up === true) {
            const msg = cause.response.data.detail || 'Please re-authenticate with your password.';
            setStepUpRequired(true);
            setStepUpError(msg);
            return msg;
        }
        return null;
    };

    // Re-authenticate with a password to upgrade the session from face to password
    // auth, unlocking sensitive operations again.
    const stepUpWithPassword = async (password) => {
        setLoading(true);
        setError(null);
        setStepUpRequired(false);
        setStepUpError(null);
        try {
            const response = await authApi.stepUp(password);
            if (response?.access && response?.refresh) {
                // Update tokens in storage without creating a new session
                window.localStorage.setItem('learnwise:access-token', response.access);
                window.localStorage.setItem('learnwise:refresh-token', response.refresh);
                return { success: true };
            }
            throw new Error('Step-up authentication failed.');
        } catch (cause) {
            const msg = cause?.response?.data?.detail || cause.message || 'Step-up authentication failed.';
            setError(msg);
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const clearStepUp = () => {
        setStepUpRequired(false);
        setStepUpError(null);
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
        getUser,
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
        getUserSessions,
        get2FAStatus,
        getSocialAccounts,
        unlinkSocialAccount,
        revokeSession,
        revokeAllSessions,
        uploadAvatar,
        removeAvatar,
        registerFace,
        verifyFace,
        getFaceProfile,
        deleteFaceProfile,
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
        stepUpRequired,
        stepUpError,
        stepUpWithPassword,
        clearStepUp,
        clearError: () => setError(null),
    }), [user, loading, error, stepUpRequired, stepUpError]);

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const value = useContext(AuthContext);
    if (!value)
        throw new Error('useAuth must be used inside AuthProvider');
    return value;
}