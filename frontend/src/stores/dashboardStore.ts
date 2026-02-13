import { create } from 'zustand';
import type { PortfolioDashboard, PipelineDashboard } from '@/types/api';

interface DashboardState {
  portfolio: PortfolioDashboard | null;
  pipeline: PipelineDashboard | null;
  isLoading: boolean;
  lastFetched: number | null;

  setPortfolio: (data: PortfolioDashboard) => void;
  setPipeline: (data: PipelineDashboard) => void;
  setLoading: (loading: boolean) => void;
  invalidate: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  portfolio: null,
  pipeline: null,
  isLoading: false,
  lastFetched: null,

  setPortfolio: (data) => set({ portfolio: data, lastFetched: Date.now(), isLoading: false }),
  setPipeline: (data) => set({ pipeline: data, isLoading: false }),
  setLoading: (loading) => set({ isLoading: loading }),
  invalidate: () => set({ lastFetched: null }),
}));
