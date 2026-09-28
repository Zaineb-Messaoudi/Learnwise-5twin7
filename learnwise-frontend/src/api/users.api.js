import { apiRequest } from './client';
export const usersApi = {
    list: () => apiRequest('/users/'),
    detail: (id) => apiRequest(`/users/${id}/`),
};
