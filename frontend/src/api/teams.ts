import { api } from './client';
import type { TeamOut, TeamMemberOut, PaginatedResponse } from '@/types/api';

interface TeamCreate {
  name: string;
  description?: string;
  department?: string;
  organization?: string;
  manager_id?: string;
}

export const teamsApi = {
  list: (params?: { department?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<TeamOut>>('/api/teams', params),

  get: (id: string) =>
    api.get<TeamOut>(`/api/teams/${id}`),

  create: (data: TeamCreate) =>
    api.post<TeamOut>('/api/teams', data),

  update: (id: string, data: Partial<TeamCreate>) =>
    api.patch<TeamOut>(`/api/teams/${id}`, data),

  delete: (id: string) =>
    api.delete(`/api/teams/${id}`),

  members: (id: string) =>
    api.get<TeamMemberOut[]>(`/api/teams/${id}/members`),

  addMember: (id: string, userId: string, role?: string) =>
    api.post(`/api/teams/${id}/members`, { user_id: userId, role_in_team: role }),

  removeMember: (id: string, userId: string) =>
    api.delete(`/api/teams/${id}/members/${userId}`),
};
