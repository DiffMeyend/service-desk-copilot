/**
 * React Query hooks for intake operations
 */

import { useMutation } from '@tanstack/react-query';
import { parseTicket } from '../api/intake';
import type { ParseTicketRequest } from '../types/contextPayload';

export function useParseTicket() {
  return useMutation({
    mutationFn: (request: ParseTicketRequest) => parseTicket(request),
  });
}
