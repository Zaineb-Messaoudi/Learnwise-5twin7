import { createContext, useContext, useEffect, useMemo, useState } from 'react';
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
    const logout = () => clearSession();
    useEffect(() => {
        const handleExpired = () => clearSession();
        window.addEventListener('learnwise:auth-expired', handleExpired);
        return () => window.removeEventListener('learnwise:auth-expired', handleExpired);
    }, []);
    const value = useMemo(() => ({ user, login, updateUser, logout, isAuthenticated: Boolean(user) }), [user]);
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value)
    throw new Error('useAuth must be used inside AuthProvider'); return value; }
