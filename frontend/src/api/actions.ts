import { api } from './client';
import type { ActionItemOut, PaginatedResponse } from '@/types/api';

interface ActionItemCreate {
  initiative_id: string;
  title: string;
  description?: string;
  assigned_to?: string;
  priority?: string;
  due_date?: string;
}

export const actionsApi = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    api.get<PaginatedResponse<ActionItemOut>>('/api/actions', params),

  get: (id: string) =>
    api.get<ActionItemOut>(`/api/actions/${id}`),

  create: (data: ActionItemCreate) =>
    api.post<ActionItemOut>('/api/actions', data),

  update: (id: string, data: Partial<ActionItemCreate> & { status?: string }) =>
    api.patch<ActionItemOut>(`/api/actions/${id}`, data),

  delete: (id: string) =>
    api.delete(`/api/actions/${id}`),
};
