import React from 'react';
import { Outlet } from 'react-router-dom';
import { ThemeToggle } from '@/components/common/theme-toggle';

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold">IoT-DevSim v2</h1>
          </div>
          
          <div className="flex items-center space-x-4">
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
