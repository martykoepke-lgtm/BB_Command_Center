import { api } from './client';

export interface ArtifactOut {
  id: string;
  phase_id: string;
  artifact_type: string;
  title: string;
  content: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export const artifactsApi = {
  list: (phaseId: string) =>
    api.get<ArtifactOut[]>(`/api/phases/${phaseId}/artifacts`),

  get: (id: string) =>
    api.get<ArtifactOut>(`/api/artifacts/${id}`),

  create: (phaseId: string, data: { artifact_type: string; title: string; content: Record<string, unknown> }) =>
    api.post<ArtifactOut>(`/api/phases/${phaseId}/artifacts`, data),

  update: (id: string, data: Partial<{ title: string; content: Record<string, unknown>; status: string }>) =>
    api.patch<ArtifactOut>(`/api/artifacts/${id}`, data),

  delete: (id: string) =>
    api.delete(`/api/artifacts/${id}`),
};
