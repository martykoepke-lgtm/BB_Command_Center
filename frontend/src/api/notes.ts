import { api } from './client';

export interface NoteOut {
  id: string;
  initiative_id: string;
  phase_id: string | null;
  author_id: string;
  note_type: string;
  content: string;
  created_at: string;
}

export const notesApi = {
  list: (initiativeId: string) =>
    api.get<NoteOut[]>(`/api/initiatives/${initiativeId}/notes`),

  create: (initiativeId: string, data: { note_type?: string; content: string }) =>
    api.post<NoteOut>(`/api/initiatives/${initiativeId}/notes`, data),

  delete: (id: string) =>
    api.delete(`/api/notes/${id}`),
};
