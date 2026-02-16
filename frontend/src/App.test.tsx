import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from './App';

vi.mock('@/app/providers/simple-providers', () => ({
  AppProviders: () => <div>Mock App Providers</div>,
}));

describe('App', () => {
  it('renders app providers shell', () => {
    render(<App />);
    expect(screen.getByText('Mock App Providers')).toBeInTheDocument();
  });
});
