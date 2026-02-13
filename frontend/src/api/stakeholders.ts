import { api } from './client';

export interface StakeholderOut {
  initiative_id: string;
  user_id: string;
  role: string;
  added_at: string;
  user_name: string | null;
  user_email: string | null;
}

export interface ExternalStakeholderOut {
  id: string;
  initiative_id: string;
  name: string;
  title: string | null;
  organization: string | null;
  email: string | null;
  phone: string | null;
  role: string | null;
  created_at: string;
}

export const stakeholdersApi = {
  list: (initiativeId: string) =>
    api.get<StakeholderOut[]>(`/api/initiatives/${initiativeId}/stakeholders`),

  add: (initiativeId: string, data: { user_id: string; role: string }) =>
    api.post<StakeholderOut>(`/api/initiatives/${initiativeId}/stakeholders`, data),

  remove: (initiativeId: string, userId: string) =>
    api.delete(`/api/initiatives/${initiativeId}/stakeholders/${userId}`),

  listExternal: (initiativeId: string) =>
    api.get<ExternalStakeholderOut[]>(`/api/initiatives/${initiativeId}/external-stakeholders`),

  addExternal: (initiativeId: string, data: { name: string; title?: string; organization?: string; email?: string; role?: string }) =>
    api.post<ExternalStakeholderOut>(`/api/initiatives/${initiativeId}/external-stakeholders`, data),

  removeExternal: (id: string) =>
    api.delete(`/api/external-stakeholders/${id}`),
};
