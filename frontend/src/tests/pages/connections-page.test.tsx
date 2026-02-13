import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { MemoryRouter } from 'react-router-dom';

import ConnectionsPage from '@/pages/connections-page';

vi.mock('@/hooks/useConnections', () => {
  return {
    useConnections: () => ({
      data: {
        items: [],
        total: 0,
        skip: 0,
        limit: 50,
        has_next: false,
        has_prev: false,
      },
      isLoading: false,
      isError: false,
      error: null,
    }),
    useTestConnection: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
    useDeleteConnection: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
    useCreateConnection: () => ({
      mutateAsync: vi.fn(),
      isPending: false,
      error: null,
      reset: vi.fn(),
    }),
  };
});

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

describe('ConnectionsPage', () => {
  it('renders empty state and opens create dialog', () => {
    render(
      <MemoryRouter>
        <ConnectionsPage />
      </MemoryRouter>
    );

    expect(screen.getByText('Conexiones')).toBeInTheDocument();
    expect(screen.getByText('No hay conexiones')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: /crear/i })[0]);
    expect(screen.getByText('Nueva conexión')).toBeInTheDocument();
  });
});
