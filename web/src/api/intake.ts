/**
 * API functions for intake operations
 */

import { apiClient } from './client';
import type { ParseTicketRequest, ParseTicketResponse } from '../types/contextPayload';

export async function parseTicket(request: ParseTicketRequest): Promise<ParseTicketResponse> {
  const response = await apiClient.post<ParseTicketResponse>('/api/v1/intake/parse', request);
  return response.data;
}
