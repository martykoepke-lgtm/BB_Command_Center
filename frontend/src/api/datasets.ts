import { api, ApiError } from './client';

export interface DatasetOut {
  id: string;
  initiative_id: string;
  name: string;
  file_type: string;
  row_count: number | null;
  column_count: number | null;
  columns: Record<string, unknown> | null;
  profile: Record<string, unknown> | null;
  uploaded_at: string;
}

export const datasetsApi = {
  list: (initiativeId: string) =>
    api.get<DatasetOut[]>(`/api/initiatives/${initiativeId}/datasets`),

  get: (id: string) =>
    api.get<DatasetOut>(`/api/datasets/${id}`),

  upload: async (initiativeId: string, file: File): Promise<DatasetOut> => {
    const token = localStorage.getItem('bb_token');
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`/api/initiatives/${initiativeId}/datasets`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        detail = err.detail ?? detail;
      } catch { /* ignore */ }
      throw new ApiError(response.status, detail);
    }

    return response.json();
  },

  delete: (id: string) =>
    api.delete(`/api/datasets/${id}`),

  preview: (id: string, rows?: number) =>
    api.get<Record<string, unknown>>(`/api/datasets/${id}/preview`, { rows }),
};
