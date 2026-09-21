import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiService } from '../services/api';

interface User {
  id: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loginWithGmail: () => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const AUTH_POPUP_TIMEOUT_MS = 300000;
const AUTH_POPUP_CLOSED_POLL_MS = 500;
const SESSION_USER_KEY = 'classwire:v1:session-user';
const SESSION_SIGNED_OUT_KEY = 'classwire:v1:explicitly-signed-out';
const LEGACY_USER_KEY = 'user';
const TIMETABLE_KEY_PREFIX = 'classwire:v2:last-timetable:';

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
  const authTimeoutRef = React.useRef<number | null>(null);
  const authPopupCheckRef = React.useRef<number | null>(null);
  const pendingGmailAuthRef = React.useRef<((success: boolean) => void) | null>(null);

  const clearAuthTimeout = React.useCallback(() => {
    if (authTimeoutRef.current !== null) {
      window.clearTimeout(authTimeoutRef.current);
      authTimeoutRef.current = null;
    }
  }, []);

  const clearAuthPopupCheck = React.useCallback(() => {
    if (authPopupCheckRef.current !== null) {
      window.clearInterval(authPopupCheckRef.current);
      authPopupCheckRef.current = null;
    }
  }, []);

  const finishPendingGmailAuth = React.useCallback((success: boolean) => {
    clearAuthTimeout();
    clearAuthPopupCheck();

    if (pendingGmailAuthRef.current) {
      pendingGmailAuthRef.current(success);
      pendingGmailAuthRef.current = null;
    }
  }, [clearAuthPopupCheck, clearAuthTimeout]);

  useEffect(() => {
    const restoreSession = async () => {
      try {
        await apiService.initialize();
        const response = await apiService.getSession();
        setUser(response.user);
        cacheUser(response.user);
      } catch {
        setUser(null);
        cacheUser(null);
      } finally {
        setLoading(false);
      }
    };

    // Check for OAuth callback parameters (mobile redirect flow)
    const urlParams = new URLSearchParams(window.location.search);
    
    if (urlParams.has('auth')) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    restoreSession();
    
    // Listen for Gmail OAuth callback
    const handleGmailAuthMessage = async (event: MessageEvent) => {
      const apiBaseOrigin = apiService.getBaseOrigin();
      
      if (event.origin !== apiBaseOrigin) {
        return;
      }

      if (!event.data || typeof event.data !== 'object') {
        return;
      }
      
      if (event.data.type === 'GMAIL_AUTH_SUCCESS') {
        try {
          const response = await apiService.getSession();
          setUser(response.user);
          cacheUser(response.user);
          finishPendingGmailAuth(true);
        } catch {
          setUser(null);
          cacheUser(null);
          finishPendingGmailAuth(false);
        } finally {
          setLoading(false);
        }
      } else if (event.data.type === 'GMAIL_AUTH_ERROR') {
        setLoading(false);
        finishPendingGmailAuth(false);
      }
    };
    
    window.addEventListener('message', handleGmailAuthMessage);
    return () => {
      clearAuthTimeout();
      clearAuthPopupCheck();
      window.removeEventListener('message', handleGmailAuthMessage);
    };
  }, [clearAuthPopupCheck, clearAuthTimeout, finishPendingGmailAuth]);

  const loginWithGmail = async (): Promise<boolean> => {
    try {
      await apiService.initialize();

      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

      if (isMobile) {
        const apiBaseOrigin = apiService.getBaseOrigin();
        const mobileAuthUrl = `${apiBaseOrigin}/api/auth/gmail?redirect=1&frontend_origin=${encodeURIComponent(window.location.origin)}`;
        window.location.href = mobileAuthUrl;
        return true;
      }

      const authData = await apiService.getGmailAuthUrl(window.location.origin);
      const popup = window.open(
        authData.auth_url,
        'gmail-auth',
        'width=500,height=600,scrollbars=yes,resizable=yes'
      );
      
      if (!popup) {
        throw new Error('Popup blocked. Please allow popups for this site.');
      }
      
      clearAuthTimeout();
      clearAuthPopupCheck();

      return await new Promise<boolean>((resolve) => {
        pendingGmailAuthRef.current = resolve;

        authTimeoutRef.current = window.setTimeout(() => {
          finishPendingGmailAuth(false);
        }, AUTH_POPUP_TIMEOUT_MS);

        authPopupCheckRef.current = window.setInterval(() => {
          if (popup.closed) {
            finishPendingGmailAuth(false);
          }
        }, AUTH_POPUP_CLOSED_POLL_MS);
      });
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

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    loginWithGmail,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
