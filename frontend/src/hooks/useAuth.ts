import { useState } from 'react';

export interface AuthState {
  isAuthenticated: boolean;
}

export function useAuth() {
  const [state] = useState<AuthState>({ isAuthenticated: false });
  return state;
}
