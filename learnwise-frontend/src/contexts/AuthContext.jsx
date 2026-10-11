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

    const socialLogin = async (provider, accessToken, role = 'etudiant') => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.socialLogin(provider, accessToken, role);
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