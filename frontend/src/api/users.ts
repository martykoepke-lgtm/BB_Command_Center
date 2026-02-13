import { api } from './client';
import type { UserOut, PaginatedResponse } from '@/types/api';

export const usersApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<UserOut>>('/api/users', params),

  get: (id: string) =>
    api.get<UserOut>(`/api/users/${id}`),

  update: (id: string, data: Partial<UserOut>) =>
    api.patch<UserOut>(`/api/users/${id}`, data),
};
