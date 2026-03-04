/**
 * API functions for branch pack operations
 */

import { apiClient } from './client';
import type { BranchPackSummary, BranchPackDetail } from '../types/contextPayload';

/**
 * List all available branch packs
 */
export async function listBranchPacks(): Promise<BranchPackSummary[]> {
  const response = await apiClient.get<BranchPackSummary[]>('/api/v1/branch-packs');
  return response.data;
}

/**
 * Get detailed information about a branch pack
 */
export async function getBranchPack(packId: string): Promise<BranchPackDetail> {
  const response = await apiClient.get<BranchPackDetail>(`/api/v1/branch-packs/${packId}`);
  return response.data;
}
