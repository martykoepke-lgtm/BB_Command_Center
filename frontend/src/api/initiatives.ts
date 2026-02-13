import { api } from './client';
import type {
  InitiativeOut,
  InitiativeSummary,
  InitiativeCreate,
  PaginatedResponse,
  PhaseOut,
} from '@/types/api';

export const initiativesApi = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    api.get<PaginatedResponse<InitiativeSummary>>('/api/initiatives', params),

  get: (id: string) =>
    api.get<InitiativeOut>(`/api/initiatives/${id}`),

  create: (data: InitiativeCreate) =>
    api.post<InitiativeOut>('/api/initiatives', data),

  update: (id: string, data: Partial<InitiativeOut>) =>
    api.patch<InitiativeOut>(`/api/initiatives/${id}`, data),

  delete: (id: string) =>
    api.delete(`/api/initiatives/${id}`),

  getPhases: (id: string) =>
    api.get<PhaseOut[]>(`/api/initiatives/${id}/phases`),

  advancePhase: (id: string) =>
    api.post<InitiativeOut>(`/api/initiatives/${id}/advance-phase`),
};
