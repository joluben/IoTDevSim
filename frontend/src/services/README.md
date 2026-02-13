# Authentication System Documentation

## Overview

The IoT-DevSim v2 frontend implements a robust authentication system with JWT token management, automatic refresh, session timeout, and activity tracking.

## Architecture

### Core Components

1. **AuthService** (`auth.service.ts`) - Centralized authentication API service with Axios interceptors
2. **ApiClient** (`api.client.ts`) - Global API client with automatic token injection
3. **AuthStore** (`auth-store.ts`) - Zustand store for authentication state management
4. **AuthInitializer** (`auth.initializer.ts`) - App startup authentication logic
5. **ActivityTracker** (`useActivityTracker.ts`) - User activity monitoring hook

### Key Features

- ✅ **JWT Token Management** - Secure storage with basic encryption
- ✅ **Automatic Token Refresh** - Proactive refresh before expiration
- ✅ **Session Timeout** - 30-minute inactivity timeout
- ✅ **Activity Tracking** - Mouse, keyboard, and touch event monitoring
- ✅ **Axios Interceptors** - Automatic token injection and 401 handling
- ✅ **Permission-Based Access** - Role and permission checking
- ✅ **Secure Storage** - Encrypted localStorage with fallback

## Usage Examples

### Basic Authentication

```typescript
import { useAuthStore } from '@/app/store/auth-store';

function LoginComponent() {
  const { login, isLoading, error } = useAuthStore();

  const handleLogin = async (email: string, password: string) => {
    try {
      await login(email, password);
      // User is now authenticated, tokens are stored automatically
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      handleLogin(formData.get('email'), formData.get('password'));
    }}>
      <input name="email" type="email" required />
      <input name="password" type="password" required />
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
```

### Using API Client

```typescript
import { apiClient } from '@/services/api.client';

// API calls automatically include Authorization header
async function fetchDevices() {
  try {
    const devices = await apiClient.get('/devices');
    return devices;
  } catch (error) {
    // 401 errors are handled automatically (token refresh or logout)
    console.error('Failed to fetch devices:', error);
  }
}

// File upload with progress
async function uploadFile(file: File) {
  try {
    const result = await apiClient.upload('/devices/import', file, (progress) => {
      console.log(`Upload progress: ${progress}%`);
    });
    return result;
  } catch (error) {
    console.error('Upload failed:', error);
  }
}
```

### Permission Checking

```typescript
import { useAuthStore } from '@/app/store/auth-store';

function AdminPanel() {
  const { hasRole, hasPermission } = useAuthStore();

  if (!hasRole('admin')) {
    return <div>Access denied. Admin role required.</div>;
  }

  return (
    <div>
      <h1>Admin Panel</h1>
      {hasPermission('analytics:view') && (
        <button>View Analytics</button>
      )}
      {hasPermission('users:manage') && (
        <button>Manage Users</button>
      )}
    </div>
  );
}
```

### Manual Activity Updates

```typescript
import { useManualActivityUpdate } from '@/hooks/useActivityTracker';

function ApiComponent() {
  const updateActivity = useManualActivityUpdate();

  const handleApiCall = async () => {
    try {
      const result = await apiClient.post('/devices', deviceData);
      
      // Update activity after successful API call
      updateActivity();
      
      return result;
    } catch (error) {
      console.error('API call failed:', error);
    }
  };

  return <button onClick={handleApiCall}>Create Device</button>;
}
```

### Session Management

```typescript
import { useAuthStore } from '@/app/store/auth-store';

function SessionStatus() {
  const { 
    isAuthenticated, 
    isSessionActive, 
    lastActivity, 
    checkSession 
  } = useAuthStore();

  React.useEffect(() => {
    // Check session validity periodically
    const interval = setInterval(() => {
      if (isAuthenticated) {
        checkSession();
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [isAuthenticated, checkSession]);

  if (!isAuthenticated) {
    return <div>Not authenticated</div>;
  }

  if (!isSessionActive) {
    return <div>Session expired. Please log in again.</div>;
  }

  return (
    <div>
      Session active. Last activity: {new Date(lastActivity).toLocaleString()}
    </div>
  );
}
```

## Configuration

### Environment Variables

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:3000/api
VITE_WS_URL=ws://localhost:3000/ws

# Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_WEBSOCKET=true
VITE_ENABLE_BETA=false
```

### Constants Configuration

```typescript
// src/app/config/constants.ts
export const AUTH_CONFIG = {
  tokenKey: 'iot-devsim-token',
  refreshTokenKey: 'iot-devsim-refresh-token',
  tokenExpiration: 24 * 60 * 60 * 1000, // 24 hours
  refreshThreshold: 5 * 60 * 1000, // 5 minutes before expiration
} as const;
```

## Security Considerations

### Token Storage

- Tokens are stored in localStorage with basic base64 encoding
- In production, consider implementing proper encryption
- For maximum security, consider httpOnly cookies (requires backend changes)

### XSS Protection

- Input sanitization should be implemented at the API level
- CSP headers should be configured
- Avoid using `dangerouslySetInnerHTML`

### CSRF Protection

- API should implement CSRF tokens for state-changing operations
- SameSite cookie attributes should be configured

## Error Handling

### Common Error Scenarios

1. **401 Unauthorized** - Handled automatically with token refresh
2. **403 Forbidden** - User lacks required permissions
3. **Network Errors** - Retry logic with exponential backoff
4. **Token Refresh Failure** - Automatic logout and redirect to login

### Custom Error Handling

```typescript
import { apiClient } from '@/services/api.client';

// Set up global unauthorized callback
apiClient.setUnauthorizedCallback(() => {
  // Custom logic for unauthorized errors
  console.log('User session expired');
  // Redirect to login page or show modal
});
```

## Testing

### Unit Tests

```typescript
import { authService } from '@/services/auth.service';
import { useAuthStore } from '@/app/store/auth-store';

describe('AuthService', () => {
  test('should login successfully', async () => {
    const mockResponse = {
      user: { id: '1', email: 'test@example.com', name: 'Test User' },
      token: 'mock-token',
      refreshToken: 'mock-refresh-token',
      expiresIn: 3600,
    };

    // Mock API response
    jest.spyOn(authService, 'login').mockResolvedValue(mockResponse);

    const result = await authService.login({
      email: 'test@example.com',
      password: 'password123',
    });

    expect(result).toEqual(mockResponse);
  });
});
```

### Integration Tests

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProviders } from '@/app/providers';
import LoginComponent from './LoginComponent';

test('should handle login flow', async () => {
  render(
    <AppProviders>
      <LoginComponent />
    </AppProviders>
  );

  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'test@example.com' },
  });
  
  fireEvent.change(screen.getByLabelText(/password/i), {
    target: { value: 'password123' },
  });

  fireEvent.click(screen.getByRole('button', { name: /login/i }));

  await waitFor(() => {
    expect(screen.getByText(/welcome/i)).toBeInTheDocument();
  });
});
```

## Troubleshooting

### Common Issues

1. **Tokens not persisting** - Check localStorage permissions and storage limits
2. **Session timeout too aggressive** - Adjust timeout values in constants
3. **Activity tracking not working** - Ensure event listeners are properly attached
4. **API calls failing** - Check network connectivity and API endpoint configuration

### Debug Mode

```typescript
// Enable debug logging
localStorage.setItem('debug', 'auth:*');

// Check token status
console.log('Current token:', authService.getToken());
console.log('Is authenticated:', authService.isAuthenticated());
```
