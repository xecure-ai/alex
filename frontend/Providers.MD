# React Provider Pattern

The Provider pattern is a powerful React design pattern that uses Context API to share data across the component tree without prop drilling. This pattern is essential for managing global state, themes, authentication, and other cross-cutting concerns.

## Table of Contents
- [Basic Concept](#basic-concept)
- [Creating a Provider](#creating-a-provider)
- [Complete Example: Theme Provider](#complete-example-theme-provider)
- [Complete Example: Auth Provider](#complete-example-auth-provider)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

---

## Basic Concept

The Provider pattern consists of three main parts:
1. **Context**: Created using `React.createContext()`
2. **Provider Component**: Wraps the component tree and provides the context value
3. **Custom Hook**: Simplifies consuming the context

---

## Creating a Provider

### Step 1: Define the Context and Types

```typescript
import { createContext, useContext, ReactNode } from 'react';

// Define the shape of your context data
interface MyContextType {
  value: string;
  setValue: (value: string) => void;
}

// Create context with undefined as default (will be provided by Provider)
const MyContext = createContext<MyContextType | undefined>(undefined);
```

### Step 2: Create the Provider Component

```typescript
interface MyProviderProps {
  children: ReactNode;
}

export function MyProvider({ children }: MyProviderProps) {
  const [value, setValue] = useState<string>('');

  // Memoize the context value to prevent unnecessary re-renders
  const contextValue = useMemo(
    () => ({
      value,
      setValue,
    }),
    [value]
  );

  return (
    <MyContext.Provider value={contextValue}>
      {children}
    </MyContext.Provider>
  );
}
```

### Step 3: Create a Custom Hook

```typescript
export function useMyContext() {
  const context = useContext(MyContext);
  
  if (context === undefined) {
    throw new Error('useMyContext must be used within MyProvider');
  }
  
  return context;
}
```

---

## Complete Example: Theme Provider

**File: `contexts/ThemeContext.tsx`**

```typescript
import { createContext, useContext, useState, useEffect, useMemo, ReactNode } from 'react';

// Define theme types
type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

// Create context
const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Provider component
interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: Theme;
}

export function ThemeProvider({ children, defaultTheme = 'light' }: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(defaultTheme);

  // Load theme from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as Theme | null;
    if (savedTheme) {
      setTheme(savedTheme);
    }
  }, []);

  // Save theme to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const contextValue = useMemo(
    () => ({
      theme,
      toggleTheme,
      setTheme,
    }),
    [theme]
  );

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}

// Custom hook
export function useTheme() {
  const context = useContext(ThemeContext);
  
  if (context === undefined) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  
  return context;
}
```

---

## Complete Example: Auth Provider

**File: `contexts/AuthContext.tsx`**

```typescript
import { createContext, useContext, useState, useEffect, useMemo, ReactNode } from 'react';

// Define user and auth types
interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider component
interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const userData = await response.json();
      setUser(userData);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const updateUser = (updatedUser: User) => {
    setUser(updatedUser);
  };

  const contextValue = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
      updateUser,
    }),
    [user, isLoading]
  );

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook
export function useAuth() {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  
  return context;
}
```

---

## Usage Examples

### 1. Wrapping Your App with Providers

**File: `pages/_app.tsx` (Next.js)**

```typescript
import type { AppProps } from 'next/app';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { AuthProvider } from '@/contexts/AuthContext';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ThemeProvider defaultTheme="light">
      <AuthProvider>
        <Component {...pageProps} />
      </AuthProvider>
    </ThemeProvider>
  );
}
```

### 2. Using the Theme Provider

**File: `components/ThemeToggle.tsx`**

```typescript
import { useTheme } from '@/contexts/ThemeContext';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-800"
    >
      {theme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode'}
    </button>
  );
}
```

### 3. Using the Auth Provider

**File: `components/LoginForm.tsx`**

```typescript
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export function LoginForm() {
  const { login, isLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        disabled={isLoading}
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        disabled={isLoading}
      />
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
}
```

**File: `components/UserProfile.tsx`**

```typescript
import { useAuth } from '@/contexts/AuthContext';

export function UserProfile() {
  const { user, isAuthenticated, logout } = useAuth();

  if (!isAuthenticated || !user) {
    return <div>Please log in</div>;
  }

  return (
    <div>
      <h2>Welcome, {user.name}!</h2>
      <p>Email: {user.email}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

### 4. Protected Route Component

```typescript
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/router';
import { useEffect } from 'react';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
```

---

## Best Practices

### 1. **Use TypeScript for Type Safety**
Always define proper types for your context to catch errors at compile time.

### 2. **Memoize Context Values**
Use `useMemo` to prevent unnecessary re-renders:
```typescript
const contextValue = useMemo(
  () => ({ value, setValue }),
  [value]
);
```

### 3. **Create Custom Hooks**
Always provide a custom hook that includes error checking:
```typescript
export function useMyContext() {
  const context = useContext(MyContext);
  if (context === undefined) {
    throw new Error('useMyContext must be used within MyProvider');
  }
  return context;
}
```

### 4. **Split Large Contexts**
Don't put everything in one context. Split by concern:
- `AuthContext` for authentication
- `ThemeContext` for theming
- `NotificationContext` for notifications

### 5. **Avoid Over-Using Context**
Context is not a replacement for all state management. Use it for:
- Global app state (theme, auth, locale)
- Data that many components need
- Avoiding prop drilling

Don't use it for:
- Frequently changing values (can cause performance issues)
- Local component state
- Data that only a few components need

### 6. **Provide Default Values**
Consider providing sensible defaults or initial values:
```typescript
const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  toggleTheme: () => {},
  setTheme: () => {},
});
```

### 7. **Separate Context Files**
Keep each context in its own file under a `contexts/` directory:
```
contexts/
  ├── ThemeContext.tsx
  ├── AuthContext.tsx
  └── NotificationContext.tsx
```

### 8. **Handle Loading States**
For async operations, always include loading states:
```typescript
const [isLoading, setIsLoading] = useState(true);
```

### 9. **Cleanup Side Effects**
Always cleanup subscriptions and listeners:
```typescript
useEffect(() => {
  const unsubscribe = subscribe();
  return () => unsubscribe();
}, []);
```

### 10. **Test Your Providers**
Write tests that wrap components with your providers:
```typescript
const wrapper = ({ children }) => (
  <ThemeProvider>{children}</ThemeProvider>
);

renderHook(() => useTheme(), { wrapper });
```

---

## Advanced Pattern: Compound Providers

For apps with multiple providers, create a compound provider:

**File: `contexts/AppProviders.tsx`**

```typescript
import { ReactNode } from 'react';
import { ThemeProvider } from './ThemeContext';
import { AuthProvider } from './AuthContext';

interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ThemeProvider>
      <AuthProvider>
        {children}
      </AuthProvider>
    </ThemeProvider>
  );
}
```

Then use it in your app:

```typescript
import { AppProviders } from '@/contexts/AppProviders';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <AppProviders>
      <Component {...pageProps} />
    </AppProviders>
  );
}
```

---

## Summary

The Provider pattern is essential for:
- ✅ Avoiding prop drilling
- ✅ Managing global state
- ✅ Sharing functionality across components
- ✅ Creating reusable, composable logic
- ✅ Improving code organization

Remember to use it judiciously and follow the best practices outlined above for optimal performance and maintainability.
