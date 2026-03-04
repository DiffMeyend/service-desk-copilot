/**
 * React Query hooks for ticket operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listTickets, getTicket, getTicketCSS } from '../api/tickets';
import { logResult, loadBranchPack, decide, getNextAction } from '../api/commands';
import type { LogResultRequest, LoadBranchPackRequest, DecideRequest } from '../types/contextPayload';
import { useStore } from '../store';

// Query keys
export const ticketKeys = {
  all: ['tickets'] as const,
  lists: () => [...ticketKeys.all, 'list'] as const,
  list: () => ticketKeys.lists(),
  details: () => [...ticketKeys.all, 'detail'] as const,
  detail: (id: string) => [...ticketKeys.details(), id] as const,
  css: (id: string) => [...ticketKeys.detail(id), 'css'] as const,
  nextAction: (id: string) => [...ticketKeys.detail(id), 'nextAction'] as const,
};

/**
 * Hook to list all tickets
 */
export function useTickets() {
  const setTickets = useStore((state) => state.setTickets);

  return useQuery({
    queryKey: ticketKeys.list(),
    queryFn: async () => {
      const tickets = await listTickets();
      setTickets(tickets);
      return tickets;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Hook to get a single ticket's Context Payload
 */
export function useTicket(ticketId: string | null) {
  const setContextPayload = useStore((state) => state.setContextPayload);

  return useQuery({
    queryKey: ticketKeys.detail(ticketId ?? ''),
    queryFn: async () => {
      if (!ticketId) return null;
      const cp = await getTicket(ticketId);
      setContextPayload(cp);
      return cp;
    },
    enabled: !!ticketId,
  });
}

/**
 * Hook to get CSS details for a ticket
 */
export function useTicketCSS(ticketId: string | null) {
  return useQuery({
    queryKey: ticketKeys.css(ticketId ?? ''),
    queryFn: async () => {
      if (!ticketId) return null;
      return getTicketCSS(ticketId);
    },
    enabled: !!ticketId,
  });
}

/**
 * Hook to get next action suggestion
 */
export function useNextAction(ticketId: string | null) {
  return useQuery({
    queryKey: ticketKeys.nextAction(ticketId ?? ''),
    queryFn: async () => {
      if (!ticketId) return null;
      return getNextAction(ticketId);
    },
    enabled: !!ticketId,
  });
}

/**
 * Hook for logging test results
 */
export function useLogResult(ticketId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: LogResultRequest) => logResult(ticketId, request),
    onSuccess: () => {
      // Invalidate ticket queries to refresh data
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) });
      queryClient.invalidateQueries({ queryKey: ticketKeys.css(ticketId) });
      queryClient.invalidateQueries({ queryKey: ticketKeys.nextAction(ticketId) });
    },
  });
}

/**
 * Hook for loading branch packs
 */
export function useLoadBranchPack(ticketId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: LoadBranchPackRequest) => loadBranchPack(ticketId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) });
      queryClient.invalidateQueries({ queryKey: ticketKeys.nextAction(ticketId) });
    },
  });
}

/**
 * Hook for executing DECIDE
 */
export function useDecide(ticketId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: DecideRequest = {}) => decide(ticketId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) });
      queryClient.invalidateQueries({ queryKey: ticketKeys.list() });
    },
  });
}
