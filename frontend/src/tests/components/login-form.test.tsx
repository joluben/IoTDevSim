import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

// Mock auth store before importing the component
const mockLogin = vi.fn();
const mockClearError = vi.fn();

vi.mock('@/app/store/auth-store', () => ({
  useAuthStore: () => ({
    login: mockLogin,
    isLoading: false,
    error: null,
    clearError: mockClearError,
  }),
}));

import { LoginForm } from '@/components/auth/login-form';

function renderLoginForm(props = {}) {
  return render(
    <MemoryRouter>
      <LoginForm {...props} />
    </MemoryRouter>
  );
}

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders email and password fields', () => {
    renderLoginForm();

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders forgot password link', () => {
    renderLoginForm();

    expect(screen.getByText(/forgot your password/i)).toBeInTheDocument();
  });

  it('shows password toggle button', () => {
    renderLoginForm();

    const toggleBtn = screen.getByRole('button', { name: /show password/i });
    expect(toggleBtn).toBeInTheDocument();
  });

  it('toggles password visibility on click', async () => {
    const user = userEvent.setup();
    renderLoginForm();

    const passwordInput = screen.getByPlaceholderText(/enter your password/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    const toggleBtn = screen.getByRole('button', { name: /show password/i });
    await user.click(toggleBtn);

    expect(passwordInput).toHaveAttribute('type', 'text');
  });

  it('shows validation errors on empty submit', async () => {
    const user = userEvent.setup();
    renderLoginForm();

    const submitBtn = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitBtn);

    // Wait for validation messages
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
  });

  it('shows email validation error for invalid email', async () => {
    const user = userEvent.setup();
    renderLoginForm();

    const emailInput = screen.getByPlaceholderText(/enter your email/i);
    await user.type(emailInput, 'not-an-email');
    await user.tab(); // trigger blur validation

    expect(await screen.findByText(/valid email/i)).toBeInTheDocument();
  });
});
