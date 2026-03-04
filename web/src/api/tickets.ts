/**
 * API functions for ticket operations
 */

import { apiClient } from './client';
import type {
  TicketSummary,
  ContextPayload,
  CSSResponse,
} from '../types/contextPayload';

/**
 * List all available tickets
 */
export async function listTickets(): Promise<TicketSummary[]> {
  const response = await apiClient.get<TicketSummary[]>('/api/v1/tickets');
  return response.data;
}

/**
 * Get full Context Payload for a ticket
 */
export async function getTicket(ticketId: string): Promise<ContextPayload> {
  const response = await apiClient.get<ContextPayload>(`/api/v1/tickets/${ticketId}`);
  return response.data;
}

/**
 * Get CSS score details for a ticket
 */
export async function getTicketCSS(ticketId: string): Promise<CSSResponse> {
  const response = await apiClient.get<CSSResponse>(`/api/v1/tickets/${ticketId}/css`);
  return response.data;
}
