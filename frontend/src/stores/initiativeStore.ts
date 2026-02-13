import { create } from 'zustand';
import type { InitiativeOut, InitiativeSummary, InitiativeStatus, PhaseName, Priority, Methodology } from '@/types/api';

interface InitiativeFilters {
  status?: InitiativeStatus;
  phase?: PhaseName;
  priority?: Priority;
  methodology?: Methodology;
  search?: string;
  teamId?: string;
  leadAnalystId?: string;
}

interface InitiativeState {
  initiatives: InitiativeSummary[];
  currentInitiative: InitiativeOut | null;
  filters: InitiativeFilters;
  isLoading: boolean;
  total: number;
  page: number;
  perPage: number;

  setInitiatives: (initiatives: InitiativeSummary[], total: number) => void;
  setCurrentInitiative: (initiative: InitiativeOut | null) => void;
  setFilters: (filters: Partial<InitiativeFilters>) => void;
  clearFilters: () => void;
  setLoading: (loading: boolean) => void;
  setPage: (page: number) => void;
}

export const useInitiativeStore = create<InitiativeState>((set) => ({
  initiatives: [],
  currentInitiative: null,
  filters: {},
  isLoading: false,
  total: 0,
  page: 1,
  perPage: 25,

  setInitiatives: (initiatives, total) => set({ initiatives, total, isLoading: false }),
  setCurrentInitiative: (initiative) => set({ currentInitiative: initiative }),
  setFilters: (filters) => set((s) => ({ filters: { ...s.filters, ...filters }, page: 1 })),
  clearFilters: () => set({ filters: {}, page: 1 }),
  setLoading: (loading) => set({ isLoading: loading }),
  setPage: (page) => set({ page }),
}));
