/**
 * Zustand store for QF_Wiz application state
 */

import { create } from 'zustand';
import type { ContextPayload, TicketSummary } from '../types/contextPayload';

function deepMerge<T extends object>(target: T, patch: Partial<T>): T {
  const result = { ...target };
  for (const key of Object.keys(patch) as Array<keyof T>) {
    const patchVal = patch[key];
    const targetVal = target[key];
    if (
      patchVal !== null &&
      patchVal !== undefined &&
      typeof patchVal === 'object' &&
      !Array.isArray(patchVal) &&
      targetVal !== null &&
      targetVal !== undefined &&
      typeof targetVal === 'object' &&
      !Array.isArray(targetVal)
    ) {
      result[key] = deepMerge(targetVal as object, patchVal as object) as T[keyof T];
    } else if (patchVal !== undefined) {
      result[key] = patchVal as T[keyof T];
    }
  }
  return result;
}

interface TroubleshootingStore {
  // Active session state
  activeTicketId: string | null;
  contextPayload: ContextPayload | null;
  tickets: TicketSummary[];
  isLoading: boolean;
  error: string | null;

  // WebSocket connection state
  isConnected: boolean;

  // UI state
  selectedHypothesisId: string | null;

  // Actions
  setActiveTicket: (ticketId: string | null) => void;
  setContextPayload: (cp: ContextPayload | null) => void;
  updateContextPayload: (patch: Partial<ContextPayload>) => void;
  setTickets: (tickets: TicketSummary[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setConnected: (connected: boolean) => void;
  setSelectedHypothesis: (id: string | null) => void;

  // Derived getters
  getCSSScore: () => number;
  getCSSTarget: () => number;
  getActiveHypotheses: () => ContextPayload['branches']['active_hypotheses'];
  getTestsRunCount: () => number;
}

export const useStore = create<TroubleshootingStore>((set, get) => ({
  // Initial state
  activeTicketId: null,
  contextPayload: null,
  tickets: [],
  isLoading: false,
  error: null,
  isConnected: false,
  selectedHypothesisId: null,

  // Actions
  setActiveTicket: (ticketId) => set({ activeTicketId: ticketId }),

  setContextPayload: (cp) => set({ contextPayload: cp }),

  updateContextPayload: (patch) =>
    set((state) => ({
      contextPayload: state.contextPayload
        ? deepMerge(state.contextPayload, patch)
        : null,
    })),

  setTickets: (tickets) => set({ tickets }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  setConnected: (isConnected) => set({ isConnected }),

  setSelectedHypothesis: (id) => set({ selectedHypothesisId: id }),

  // Derived getters
  getCSSScore: () => get().contextPayload?.css?.score ?? 0,

  getCSSTarget: () => get().contextPayload?.css?.target ?? 90,

  getActiveHypotheses: () => get().contextPayload?.branches?.active_hypotheses ?? [],

  getTestsRunCount: () => get().contextPayload?.evidence?.tests_run?.length ?? 0,
}));

// Selectors for common derived state
export const selectActiveTicket = (state: TroubleshootingStore) =>
  state.tickets.find((t) => t.id === state.activeTicketId);

export const selectCanDecide = (state: TroubleshootingStore) => {
  const cp = state.contextPayload;
  if (!cp) return false;
  return cp.css.score >= cp.css.target;
};

export const selectCSSScoreColor = (state: TroubleshootingStore): string => {
  const score = state.contextPayload?.css?.score ?? 0;
  if (score >= 90) return 'high';
  if (score >= 70) return 'medium';
  return 'low';
};
