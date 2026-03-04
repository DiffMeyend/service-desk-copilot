/**
 * WebSocket hook for real-time ticket updates
 */

import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useStore } from '../store';
import { ticketKeys } from './useTickets';
import type { WSMessage, ContextPayload } from '../types/contextPayload';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8787';

interface UseWebSocketOptions {
  ticketId: string | null;
  onMessage?: (message: WSMessage) => void;
}

export function useWebSocket({ ticketId, onMessage }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const queryClient = useQueryClient();
  const { setConnected, updateContextPayload } = useStore();

  const connect = useCallback(() => {
    if (!ticketId) return;

    const ws = new WebSocket(`${WS_BASE_URL}/api/v1/tickets/${ticketId}/stream`);

    ws.onopen = () => {
      console.log(`[WS] Connected to ticket ${ticketId}`);
      setConnected(true);
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      setConnected(false);

      // Attempt reconnect after 3 seconds
      reconnectTimeoutRef.current = window.setTimeout(() => {
        console.log('[WS] Attempting reconnect...');
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        console.log('[WS] Message:', message.type);

        // Handle message types
        switch (message.type) {
          case 'cp_update':
            updateContextPayload(message.payload as Partial<ContextPayload>);
            // Also invalidate queries to ensure consistency
            queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) });
            break;

          case 'css_recalculated':
            updateContextPayload({
              css: {
                ...useStore.getState().contextPayload?.css,
                score: message.payload.score,
              } as ContextPayload['css'],
            });
            queryClient.invalidateQueries({ queryKey: ticketKeys.css(ticketId) });
            break;

          case 'hypothesis_collapsed':
            // Refresh the full ticket to get updated hypotheses
            queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) });
            break;

          case 'decision_ready':
            queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketId) });
            queryClient.invalidateQueries({ queryKey: ticketKeys.list() });
            break;
        }

        // Call custom handler if provided
        onMessage?.(message);
      } catch (e) {
        console.error('[WS] Failed to parse message:', e);
      }
    };

    wsRef.current = ws;
  }, [ticketId, setConnected, updateContextPayload, queryClient, onMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnected(false);
  }, [setConnected]);

  const sendMessage = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Connect when ticketId changes, disconnect on unmount
  useEffect(() => {
    if (ticketId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [ticketId, connect, disconnect]);

  return {
    isConnected: useStore((state) => state.isConnected),
    sendMessage,
    disconnect,
    reconnect: connect,
  };
}
