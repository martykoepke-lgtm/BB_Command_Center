import { api } from './client';

export interface MetricOut {
  id: string;
  initiative_id: string;
  name: string;
  baseline: number | null;
  target: number | null;
  current: number | null;
  unit: string | null;
  created_at: string;
}

export const metricsApi = {
  list: (initiativeId: string) =>
    api.get<MetricOut[]>(`/api/initiatives/${initiativeId}/metrics`),

  create: (initiativeId: string, data: { name: string; baseline?: number; target?: number; unit?: string }) =>
    api.post<MetricOut>(`/api/initiatives/${initiativeId}/metrics`, data),

  update: (id: string, data: Partial<{ name: string; current: number; target: number }>) =>
    api.patch<MetricOut>(`/api/metrics/${id}`, data),

  delete: (id: string) =>
    api.delete(`/api/metrics/${id}`),
};
