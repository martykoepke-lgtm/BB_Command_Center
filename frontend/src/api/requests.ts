import { api } from "./client";
import type { RequestCreate, RequestOut, PaginatedResponse } from "@/types/api";

export const requestsApi = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<RequestOut>>("/api/requests", params),

  get: (id: string) =>
    api.get<RequestOut>(`/api/requests/${id}`),

  create: (data: RequestCreate) =>
    api.post<RequestOut>("/api/requests", data),

  update: (id: string, data: Partial<RequestCreate> & { status?: string; review_notes?: string }) =>
    api.patch<RequestOut>(`/api/requests/${id}`, data),

  convertToInitiative: (id: string, data: { methodology?: string; priority?: string }) =>
    api.post<{ initiative_id: string }>(`/api/requests/${id}/convert`, data),
};
