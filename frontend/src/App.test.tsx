import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from './App';

describe('App', () => {
  it('renders the main title', () => {
    render(<App />);
    expect(screen.getByText('IoT-DevSim v2 Frontend')).toBeInTheDocument();
  });

  it('shows phase 1 task 1 completion', () => {
    render(<App />);
    expect(screen.getByText('Phase 1, Task 1 - Project Setup Complete')).toBeInTheDocument();
  });

  it('renders buttons', () => {
    render(<App />);
    expect(screen.getByText('Primary Button')).toBeInTheDocument();
    expect(screen.getByText('Secondary Button')).toBeInTheDocument();
  });
});
