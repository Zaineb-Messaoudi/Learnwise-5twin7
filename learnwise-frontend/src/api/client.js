import axios from 'axios';
const API_URL = import.meta.env.VITE_API_URL || '/api/v1';
export const apiMode = import.meta.env.VITE_API_MODE || 'mock';
export const isBackendApiEnabled = apiMode === 'backend';
export const apiClient = axios.create({ baseURL: API_URL, headers: { 'Content-Type': 'application/json' } });

// Endpoints whose 401/403 answers are part of normal sign-in/sign-up UX ("Invalid credentials",
// "verify your email", "2FA required"...). They must reach the calling form untouched: no token
// refresh attempt, and no "session expired" broadcast.
const PUBLIC_AUTH_PATHS = [
    '/auth/login/', '/auth/social/', '/auth/face/verify/', '/auth/password-reset/', '/auth/verify-email/',
    '/auth/resend-verification/', '/accounts/register/', '/accounts/terms/',
];
const isPublicAuthCall = url => PUBLIC_AUTH_PATHS.some(path => (url || '').includes(path));

apiClient.interceptors.request.use(config => {
    const token = window.localStorage.getItem('learnwise:access-token');
    if (token)
        config.headers.Authorization = `Bearer ${token}`;
    return config;
});
let refreshRequest;
apiClient.interceptors.response.use(response => response, async error => {
    const original = error.config;
    const status = error.response?.status;
    if (status === 403 && /complete your profile/i.test(String(error.response?.data?.detail || ''))) {
        // The account has not finished onboarding (role / face enrolment): let the app re-sync and redirect.
        window.dispatchEvent(new Event('learnwise:onboarding-required'));
        return Promise.reject(error);
    }
    if (status !== 401 || isPublicAuthCall(original?.url)) return Promise.reject(error);
    const refresh = window.localStorage.getItem('learnwise:refresh-token');
    if (refresh && original && !original._retry && !original.url?.includes('/auth/token/refresh/')) {
        original._retry = true;
        try {
            refreshRequest ||= apiClient.post('/auth/token/refresh/', { refresh }).then(response => response.data).finally(() => { refreshRequest = null; });
            const tokens = await refreshRequest;
            if (!tokens.access) throw new Error('The refresh response did not include an access token.');
            window.localStorage.setItem('learnwise:access-token', tokens.access);
            if (tokens.refresh) window.localStorage.setItem('learnwise:refresh-token', tokens.refresh);
            original.headers = { ...original.headers, Authorization: `Bearer ${tokens.access}` };
            return apiClient.request(original);
        } catch (refreshError) {
            window.dispatchEvent(new Event('learnwise:auth-expired'));
            return Promise.reject(refreshError);
        }
    }
    window.dispatchEvent(new Event('learnwise:auth-expired'));
    return Promise.reject(error);
});
export async function apiRequest(path, options = {}) {
    const body = options.body;
    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
    const data = body && typeof body === 'object' && !isFormData ? JSON.stringify(body) : body;
    const headers = { ...options.headers };
    if (isFormData)
        headers['Content-Type'] = undefined;
    const response = await apiClient.request({
        url: path,
        method: options.method || 'GET',
        data,
        headers,
        params: options.params,
        responseType: options.responseType,
        onUploadProgress: options.onUploadProgress,
        signal: options.signal,
    });
    return options.rawResponse ? response : response.data;
}

export function createWebSocket(path) {
    const configuredApiOrigin = API_URL.startsWith('http') ? new URL(API_URL).origin : window.location.origin;
    const base = (import.meta.env.VITE_WS_URL || configuredApiOrigin.replace(/^http/, 'ws')).replace(/\/$/, '');
    const token = window.localStorage.getItem('learnwise:access-token');
    const separator = path.includes('?') ? '&' : '?';
    const authenticatedPath = token ? `${path}${separator}token=${encodeURIComponent(token)}` : path;
    return new WebSocket(`${base}${authenticatedPath.startsWith('/') ? authenticatedPath : `/${authenticatedPath}`}`);
}
