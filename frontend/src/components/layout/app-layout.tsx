import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './sidebar';
import { Header } from './header';
import { AgentProvider } from '@/contexts/agent-context';
import { FloatingAgentButton, AgentChatPanel } from '@/components/agent';

export default function AppLayout() {
  return (
    <AgentProvider>
      <div className="min-h-screen bg-background">
        {/* Header - full width */}
        <Header />
        
        <div className="flex h-[calc(100vh-4rem)]">
          {/* Sidebar */}
          <Sidebar />
          
          {/* Main content area */}
          <div className="flex flex-1 flex-col">
            {/* Main content */}
            <main className="flex-1 overflow-auto p-6">
              <Outlet />
            </main>
          </div>
        </div>

        {/* Agent chat UI — only renders if agent-service is available */}
        <FloatingAgentButton />
        <AgentChatPanel />
      </div>
    </AgentProvider>
  );
}
