import { apiRequest } from './client';
export const usersApi = {
    list: (params = {}) => apiRequest('/accounts/admin/users/', { params }),
    detail: (id) => apiRequest(`/accounts/admin/users/${id}/`),
};
