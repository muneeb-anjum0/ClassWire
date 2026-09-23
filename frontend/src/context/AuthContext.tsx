import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiService } from '../services/api';
import { BootstrapData } from '../types/api';
import { deleteLocalAccountData } from '../services/accountData';

interface User {
  id: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loginWithGmail: () => Promise<boolean>;
  logout: () => void;
  deleteAccount: () => Promise<void>;
  bootstrap: BootstrapData | null;
  loading: boolean;
  authenticationError: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const SESSION_USER_KEY = 'classwire:v1:session-user';
const SESSION_SIGNED_OUT_KEY = 'classwire:v1:explicitly-signed-out';
const LEGACY_USER_KEY = 'user';
const TIMETABLE_KEY_PREFIX = 'classwire:v2:last-timetable:';

export type AuthRedirectResult = {
  status: 'success' | 'error';
  handoff?: string;
};

export const parseAuthRedirect = (hash: string, search: string): AuthRedirectResult | null => {
  const hashParams = new URLSearchParams(hash.startsWith('#') ? hash.slice(1) : hash);
  const queryParams = new URLSearchParams(search);
  const status = hashParams.get('auth') || queryParams.get('auth');
  if (status !== 'success' && status !== 'error') return null;
  const handoff = hashParams.get('handoff') || queryParams.get('handoff') || undefined;
  return { status, handoff };
};

const clearAuthRedirectFromAddressBar = () => {
  const cleanUrl = new URL(window.location.href);
  ['auth', 'handoff', 'user_id', 'email'].forEach((key) => cleanUrl.searchParams.delete(key));
  cleanUrl.hash = '';
  window.history.replaceState({}, document.title, `${cleanUrl.pathname}${cleanUrl.search}`);
};

const readCachedUser = (): User | null => {
  try {
    if (window.localStorage.getItem(SESSION_SIGNED_OUT_KEY) === 'true') return null;
    const raw = window.localStorage.getItem(SESSION_USER_KEY) || window.localStorage.getItem(LEGACY_USER_KEY);
    if (raw) {
      const candidate = JSON.parse(raw) as Partial<User>;
      if (typeof candidate.id === 'string' && typeof candidate.email === 'string') {
        if (candidate.id.trim() && candidate.email.trim()) {
          return { id: candidate.id, email: candidate.email.trim().toLowerCase() };
        }
      }
    }

    // Migrate users who already have a locally cached timetable from before
    // the fast session marker existed. The server replaces this temporary id
    // as soon as its signed session response arrives.
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index);
      if (!key?.startsWith(TIMETABLE_KEY_PREFIX)) continue;
      const email = key.slice(TIMETABLE_KEY_PREFIX.length).trim().toLowerCase();
      if (email && email !== 'anonymous' && email.includes('@')) {
        return { id: `cached:${email}`, email };
      }
    }
    return null;
  } catch {
    return null;
  }
};

const cacheUser = (user: User | null) => {
  try {
    if (user) {
      window.localStorage.setItem(SESSION_USER_KEY, JSON.stringify(user));
      window.localStorage.removeItem(SESSION_SIGNED_OUT_KEY);
    } else {
      window.localStorage.removeItem(SESSION_USER_KEY);
      window.localStorage.removeItem(LEGACY_USER_KEY);
    }
  } catch {
    // Storage can be unavailable in private browsing; authentication still
    // works through the signed server cookie.
  }
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  // Optimistically restore the last verified identity so the cached dashboard
  // can paint immediately. The signed server session is still verified in the
  // background and wins if the cached identity is stale.
  const [user, setUser] = useState<User | null>(() => readCachedUser());
  const [loading, setLoading] = useState(true);
  const [bootstrap, setBootstrap] = useState<BootstrapData | null>(null);
  const [authenticationError, setAuthenticationError] = useState('');

  useEffect(() => {
    const restoreSession = async () => {
      try {
        await apiService.initialize();
        const response = await apiService.getBootstrap();
        setBootstrap(response);
        if (response.authenticated && response.user) {
          setUser(response.user);
          cacheUser(response.user);
        } else {
          setUser(null);
          cacheUser(null);
        }
      } catch {
        setUser(null);
        cacheUser(null);
      } finally {
        setLoading(false);
      }
    };

    const completeAuthHandoff = async (token: string) => {
      try {
        await apiService.initialize();
        await apiService.exchangeAuthHandoff(token);
        const response = await apiService.getBootstrap();
        if (!response.authenticated || !response.user) {
          throw new Error('The signed session was not established.');
        }
        setBootstrap(response);
        setUser(response.user);
        cacheUser(response.user);
        setAuthenticationError('');
      } catch {
        setBootstrap(null);
        setUser(null);
        cacheUser(null);
        setAuthenticationError('Gmail authentication could not be completed. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    const authRedirect = parseAuthRedirect(window.location.hash, window.location.search);
    if (authRedirect) {
      clearAuthRedirectFromAddressBar();
      if (authRedirect.status === 'error' || !authRedirect.handoff) {
        setUser(null);
        cacheUser(null);
        setAuthenticationError('Gmail authentication failed. Please try again.');
        setLoading(false);
        return;
      }
      void completeAuthHandoff(authRedirect.handoff);
      return;
    }

    void restoreSession();
  }, []);

  const loginWithGmail = async (): Promise<boolean> => {
    try {
      await apiService.initialize();
      setAuthenticationError('');
      window.location.assign(apiService.getGmailRedirectUrl(window.location.origin));
      return true;
    } catch (error) {
      setLoading(false);
      throw error;
    }
  };

  const logout = () => {
    setUser(null);
    cacheUser(null);
    try {
      window.localStorage.setItem(SESSION_SIGNED_OUT_KEY, 'true');
    } catch {
      // Ignore unavailable browser storage; the server logout still runs.
    }
    void apiService.logout().catch(() => undefined);
  };

  const deleteAccount = async () => {
    const email = user?.email;
    await apiService.deleteAccount();
    await deleteLocalAccountData(email);
    setBootstrap(null);
    setUser(null);
    cacheUser(null);
    try {
      window.localStorage.setItem(SESSION_SIGNED_OUT_KEY, 'true');
    } catch {
      // Server-side deletion has already completed.
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    loginWithGmail,
    logout,
    deleteAccount,
    bootstrap,
    loading,
    authenticationError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
