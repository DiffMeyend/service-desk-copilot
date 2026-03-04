/**
 * API functions for command operations
 */

import { apiClient } from './client';
import type {
  LogResultRequest,
  LogResultResponse,
  LoadBranchPackRequest,
  LoadBranchPackResponse,
  DecideRequest,
  DecideResponse,
  NextActionResponse,
} from '../types/contextPayload';

/**
 * Log a test result for a ticket
 */
export async function logResult(
  ticketId: string,
  request: LogResultRequest
): Promise<LogResultResponse> {
  const response = await apiClient.post<LogResultResponse>(
    `/api/v1/tickets/${ticketId}/log-result`,
    request
  );
  return response.data;
}

/**
 * Load a branch pack for a ticket
 */
export async function loadBranchPack(
  ticketId: string,
  request: LoadBranchPackRequest
): Promise<LoadBranchPackResponse> {
  const response = await apiClient.post<LoadBranchPackResponse>(
    `/api/v1/tickets/${ticketId}/load-branch-pack`,
    request
  );
  return response.data;
}

/**
 * Execute DECIDE command for a ticket
 */
export async function decide(
  ticketId: string,
  request: DecideRequest = {}
): Promise<DecideResponse> {
  const response = await apiClient.post<DecideResponse>(
    `/api/v1/tickets/${ticketId}/decide`,
    request
  );
  return response.data;
}

/**
 * Get suggested next action for a ticket
 */
export async function getNextAction(ticketId: string): Promise<NextActionResponse> {
  const response = await apiClient.get<NextActionResponse>(
    `/api/v1/tickets/${ticketId}/next-action`
  );
  return response.data;
}
