import axios from 'axios';
const API_URL = import.meta.env.VITE_API_URL || '/api/v1';
export const apiMode = import.meta.env.VITE_API_MODE || 'mock';
export const isBackendApiEnabled = apiMode === 'backend';
export const apiClient = axios.create({ baseURL: API_URL, headers: { 'Content-Type': 'application/json' } });
apiClient.interceptors.request.use(config => {
    const token = window.localStorage.getItem('learnwise:access-token');
    if (token)
        config.headers.Authorization = `Bearer ${token}`;
    return config;
});
let refreshRequest;
apiClient.interceptors.response.use(response => response, async error => {
    const original = error.config;
    if (error.response?.status !== 401) return Promise.reject(error);
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
    const response = await apiClient.request({ url: path, method: options.method || 'GET', data, headers, onUploadProgress: options.onUploadProgress, signal: options.signal });
    return response.data;
}
export function createWebSocket(path) {
    const base = (import.meta.env.VITE_WS_URL || window.location.origin.replace(/^http/, 'ws')).replace(/\/$/, '');
    const token = window.localStorage.getItem('learnwise:access-token');
    const url = `${base}${path.startsWith('/') ? path : `/${path}`}`;
    const sep = url.includes('?') ? '&' : '?';
    return new WebSocket(token ? `${url}${sep}token=${token}` : url);
}
