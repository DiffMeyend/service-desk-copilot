/**
 * QF_Wiz Web Application
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { RightPanel } from './components/layout/RightPanel';
import { MainWorkArea } from './components/MainWorkArea';
import { useStore } from './store';
import { useTicket } from './hooks/useTickets';
import { useWebSocket } from './hooks/useWebSocket';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

function AppContent() {
  const activeTicketId = useStore((state) => state.activeTicketId);

  // Fetch active ticket data
  useTicket(activeTicketId);

  // Connect to WebSocket for real-time updates
  useWebSocket({ ticketId: activeTicketId });

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <Header />

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Ticket list */}
        <Sidebar className="w-64 flex-shrink-0" />

        {/* Main work area */}
        <MainWorkArea className="flex-1" />

        {/* Right panel - CSS, Guardrails, Decision */}
        <RightPanel className="w-72 flex-shrink-0" />
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
