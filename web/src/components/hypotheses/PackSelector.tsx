/**
 * PackSelector - dropdown to select and load a branch pack
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listBranchPacks } from '../../api/branchPacks';
import { useLoadBranchPack } from '../../hooks/useTickets';

interface PackSelectorProps {
  ticketId: string;
  onSelect: () => void;
}

export function PackSelector({ ticketId, onSelect }: PackSelectorProps) {
  const [selectedPackId, setSelectedPackId] = useState('');

  const { data: packs, isLoading } = useQuery({
    queryKey: ['branch-packs'],
    queryFn: listBranchPacks,
  });

  const loadPackMutation = useLoadBranchPack(ticketId);

  const handleLoad = async () => {
    if (!selectedPackId) return;

    try {
      await loadPackMutation.mutateAsync({ pack_id: selectedPackId });
      onSelect();
    } catch (error) {
      console.error('Failed to load pack:', error);
    }
  };

  // Group packs by category
  const packsByCategory = packs?.reduce(
    (acc, pack) => {
      const category = pack.category || 'other';
      if (!acc[category]) acc[category] = [];
      acc[category].push(pack);
      return acc;
    },
    {} as Record<string, typeof packs>
  );

  return (
    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
      <div className="flex gap-2">
        <select
          value={selectedPackId}
          onChange={(e) => setSelectedPackId(e.target.value)}
          className="input flex-1"
          disabled={isLoading}
        >
          <option value="">Select a pack...</option>
          {packsByCategory &&
            Object.entries(packsByCategory).map(([category, categoryPacks]) => (
              <optgroup key={category} label={category}>
                {categoryPacks?.map((pack) => (
                  <option key={pack.id} value={pack.id}>
                    {pack.name} ({pack.hypothesis_count} hypotheses)
                  </option>
                ))}
              </optgroup>
            ))}
        </select>

        <button
          onClick={handleLoad}
          disabled={!selectedPackId || loadPackMutation.isPending}
          className="btn btn-primary"
        >
          {loadPackMutation.isPending ? 'Loading...' : 'Load'}
        </button>
      </div>

      {loadPackMutation.error && (
        <p className="mt-2 text-xs text-red-500">
          Failed to load pack. Please try again.
        </p>
      )}
    </div>
  );
}
