/**
 * LogResultForm - form to log test results
 */

import { useState, useEffect } from 'react';
import type { Hypothesis } from '../../types/contextPayload';
import { useLogResult } from '../../hooks/useTickets';
import { useStore } from '../../store';

interface LogResultFormProps {
  ticketId: string;
  hypotheses: Hypothesis[];
  prefillCommandId?: string;
}

export function LogResultForm({ ticketId, hypotheses, prefillCommandId }: LogResultFormProps) {
  const [commandId, setCommandId] = useState('');
  const [output, setOutput] = useState('');
  const [notes, setNotes] = useState('');
  const setPendingCommandId = useStore((s) => s.setPendingCommandId);

  useEffect(() => {
    if (!prefillCommandId) return;
    setCommandId(prefillCommandId);
    setPendingCommandId(null);
  }, [prefillCommandId, setPendingCommandId]);

  const logResultMutation = useLogResult(ticketId);

  // Collect all command refs from hypotheses
  const commandRefs = [
    ...new Set(hypotheses.flatMap((h) => h.command_refs)),
  ].filter(Boolean);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!commandId.trim() || !output.trim()) return;

    try {
      await logResultMutation.mutateAsync({
        command_id: commandId.trim(),
        output: output.trim(),
        notes: notes.trim() || undefined,
      });

      // Reset form on success
      setCommandId('');
      setOutput('');
      setNotes('');
    } catch (error) {
      console.error('Failed to log result:', error);
    }
  };

  return (
    <div className="card p-4">
      <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
        <svg
          className="w-4 h-4 text-primary-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
          />
        </svg>
        Log Result
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Command ID */}
        <div>
          <label htmlFor="commandId" className="label block mb-1">
            Command ID
          </label>
          <div className="flex gap-2">
            <input
              id="commandId"
              type="text"
              value={commandId}
              onChange={(e) => setCommandId(e.target.value)}
              placeholder="e.g., ping_test, driver_check"
              className="input flex-1"
            />
            {commandRefs.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) setCommandId(e.target.value);
                }}
                className="input w-auto"
              >
                <option value="">Quick select...</option>
                {commandRefs.map((ref) => (
                  <option key={ref} value={ref}>
                    {ref}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Output */}
        <div>
          <label htmlFor="output" className="label block mb-1">
            Output
          </label>
          <textarea
            id="output"
            value={output}
            onChange={(e) => setOutput(e.target.value)}
            placeholder="Paste command output here..."
            rows={4}
            className="input resize-y"
          />
        </div>

        {/* Notes (optional) */}
        <div>
          <label htmlFor="notes" className="label block mb-1">
            Notes <span className="text-slate-400">(optional)</span>
          </label>
          <input
            id="notes"
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Brief interpretation or observation..."
            className="input"
          />
        </div>

        {/* Submit */}
        <div className="flex items-center justify-between">
          <button
            type="submit"
            disabled={
              !commandId.trim() || !output.trim() || logResultMutation.isPending
            }
            className="btn btn-primary"
          >
            {logResultMutation.isPending ? 'Logging...' : 'Submit Result'}
          </button>

          {logResultMutation.data && (
            <span className="text-xs text-green-600 dark:text-green-400">
              {logResultMutation.data.message} (CSS: {logResultMutation.data.css_score})
            </span>
          )}
        </div>

        {logResultMutation.error && (
          <p className="text-xs text-red-500">
            Failed to log result. Please try again.
          </p>
        )}
      </form>
    </div>
  );
}
