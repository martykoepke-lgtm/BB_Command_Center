import { api } from './client';

export interface MyInitiativeSummary {
  id: string;
  initiative_number: string;
  title: string;
  methodology: string;
  initiative_type: string | null;
  priority: string;
  status: string;
  current_phase: string;
  start_date: string | null;
  target_completion: string | null;
  created_at: string;
}

export interface MyActionItem {
  id: string;
  initiative_id: string;
  initiative_number: string | null;
  initiative_title: string | null;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface MyWorkStats {
  active_initiatives: number;
  open_actions: number;
  overdue_actions: number;
  due_this_week: number;
}

export interface MyWorkResponse {
  stats: MyWorkStats;
  initiatives: MyInitiativeSummary[];
  actions: MyActionItem[];
}

export const myWorkApi = {
  get: () => api.get<MyWorkResponse>('/api/my-work'),
};
