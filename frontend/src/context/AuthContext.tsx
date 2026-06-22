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
  const [user, setUser] = useState<User | null>(null);
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
      } catch {
        setUser(null);
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
          finishPendingGmailAuth(true);
        } catch {
          setUser(null);
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
