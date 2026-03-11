/**
 * ParseTicketModal - paste raw ticket text, get triage result from Claude
 */

import { useState } from 'react';
import { useParseTicket } from '../../hooks/useIntake';

interface ParseTicketModalProps {
  onClose: () => void;
}

export function ParseTicketModal({ onClose }: ParseTicketModalProps) {
  const [rawText, setRawText] = useState('');
  const parseMutation = useParseTicket();

  const handleParse = () => {
    const text = rawText.trim();
    if (!text) return;
    parseMutation.mutate({ raw_text: text });
  };

  const result = parseMutation.data;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-2xl mx-4 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
            <svg className="w-4 h-4 text-violet-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Parse Ticket
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <label className="label block mb-1 text-xs">Raw Ticket Text</label>
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste the raw ticket dump here..."
              rows={10}
              className="input resize-y w-full text-xs font-mono"
              disabled={parseMutation.isPending}
            />
          </div>

          {/* Triage result */}
          {result && (
            <div className="space-y-3">
              <div className="rounded-lg bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-700 p-3 space-y-2">
                {result.routing_suggestion && (
                  <p className="text-xs font-medium text-violet-700 dark:text-violet-300">
                    Routing: <span className="font-mono">{result.routing_suggestion}</span>
                  </p>
                )}
                {result.triage_reasoning && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    {result.triage_reasoning}
                  </p>
                )}
                {result.source_pack.length > 0 && (
                  <p className="text-xs text-slate-500">
                    Pack(s): <span className="font-mono">{result.source_pack.join(', ')}</span>
                  </p>
                )}
                {result.ticket_id && (
                  <p className="text-xs text-slate-500">
                    Ticket ID: <span className="font-mono">{result.ticket_id}</span>
                  </p>
                )}
              </div>

              {!result.routing_suggestion && !result.triage_reasoning && (
                <p className="text-xs text-slate-500">
                  Parsed successfully. Set <span className="font-mono">ANTHROPIC_API_KEY</span> to get Claude triage.
                </p>
              )}
            </div>
          )}

          {parseMutation.error && (
            <p className="text-xs text-red-500">Parse failed — check API connection and ticket format.</p>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2">
          <button onClick={onClose} className="btn btn-secondary text-xs">
            Close
          </button>
          <button
            onClick={handleParse}
            disabled={!rawText.trim() || parseMutation.isPending}
            className="btn btn-primary text-xs"
          >
            {parseMutation.isPending ? 'Parsing...' : 'Parse'}
          </button>
        </div>
      </div>
    </div>
  );
}
