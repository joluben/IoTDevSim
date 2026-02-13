import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './sidebar';
import { Header } from './header';

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <div className="flex h-screen">
        {/* Sidebar */}
        <Sidebar />
        
        {/* Main content area */}
        <div className="flex flex-1 flex-col">
          {/* Header */}
          <Header />
          
          {/* Main content */}
          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
