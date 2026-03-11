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

interface TriageInfo {
  routing_suggestion?: string;
  triage_reasoning?: string;
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

  // Claude triage info (set when intake/parse is called)
  triageInfo: TriageInfo | null;

  // Evidence interpretations keyed by command_id
  evidenceInterpretations: Record<string, string>;

  // Pending command ID to pre-fill LogResultForm
  pendingCommandId: string | null;

  // Claude hypothesis assessments from chat responses
  hypothesisAssessments: Record<string, 'confirmed' | 'falsified' | 'unchanged'>;

  // Actions
  setActiveTicket: (ticketId: string | null) => void;
  setContextPayload: (cp: ContextPayload | null) => void;
  updateContextPayload: (patch: Partial<ContextPayload>) => void;
  setTickets: (tickets: TicketSummary[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setConnected: (connected: boolean) => void;
  setTriageInfo: (info: TriageInfo | null) => void;

  addEvidenceInterpretation: (commandId: string, interpretation: string) => void;
  setPendingCommandId: (id: string | null) => void;
  setHypothesisAssessment: (id: string, status: 'confirmed' | 'falsified' | 'unchanged') => void;
  clearHypothesisAssessments: () => void;

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
  triageInfo: null,
  evidenceInterpretations: {},
  pendingCommandId: null,
  hypothesisAssessments: {},

  // Actions
  setActiveTicket: (ticketId) => set({ activeTicketId: ticketId, hypothesisAssessments: {} }),

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


  setTriageInfo: (info) => set({ triageInfo: info }),

  addEvidenceInterpretation: (commandId, interpretation) =>
    set((state) => ({
      evidenceInterpretations: {
        ...state.evidenceInterpretations,
        [commandId]: interpretation,
      },
    })),

  setPendingCommandId: (id) => set({ pendingCommandId: id }),

  setHypothesisAssessment: (id, status) =>
    set((state) => ({
      hypothesisAssessments: { ...state.hypothesisAssessments, [id]: status },
    })),

  clearHypothesisAssessments: () => set({ hypothesisAssessments: {} }),

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
