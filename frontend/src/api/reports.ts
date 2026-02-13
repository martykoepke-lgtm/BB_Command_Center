import { api } from './client';

export interface ReportRequest {
  report_type: string;
  initiative_id?: string;
  scope?: string;
  recipients?: string[];
}

export interface ReportOut {
  id: string;
  report_type: string;
  title: string;
  content: string;
  generated_at: string;
}

export const reportsApi = {
  generate: (data: ReportRequest) =>
    api.post<ReportOut>('/api/reports/generate', data),

  list: (params?: Record<string, string | number | boolean | undefined>) =>
    api.get<ReportOut[]>('/api/reports', params),

  get: (id: string) =>
    api.get<ReportOut>(`/api/reports/${id}`),
};
