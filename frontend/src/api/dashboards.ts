import { api } from './client';
import type { PortfolioDashboard, PipelineDashboard, TeamMetrics } from '@/types/api';

export const dashboardsApi = {
  portfolio: () =>
    api.get<PortfolioDashboard>('/api/dashboards/portfolio'),

  pipeline: () =>
    api.get<PipelineDashboard>('/api/dashboards/pipeline'),

  team: (teamId: string) =>
    api.get<TeamMetrics>(`/api/dashboards/team/${teamId}`),

  initiative: (initiativeId: string) =>
    api.get<Record<string, unknown>>(`/api/dashboards/initiative/${initiativeId}`),
};
