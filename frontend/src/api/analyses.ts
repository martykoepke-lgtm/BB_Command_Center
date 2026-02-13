import { api } from './client';
import type { AnalysisCreate, AnalysisOut } from '@/types/api';

export const analysesApi = {
  list: (initiativeId: string) =>
    api.get<AnalysisOut[]>(`/api/initiatives/${initiativeId}/analyses`),

  get: (id: string) =>
    api.get<AnalysisOut>(`/api/analyses/${id}`),

  create: (initiativeId: string, data: AnalysisCreate) =>
    api.post<AnalysisOut>(`/api/initiatives/${initiativeId}/analyses`, data),

  execute: (id: string) =>
    api.post<AnalysisOut>(`/api/analyses/${id}/execute`),

  delete: (id: string) =>
    api.delete(`/api/analyses/${id}`),
};
