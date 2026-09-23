import { useEffect, useRef, useState } from 'react';
import { DashboardTheme } from './dashboardControllerTypes';
import { getMatchMedia, THEME_STORAGE_KEY } from './utils';

export function useDashboardUiState(logout: () => void) {
  const [theme, setTheme] = useState<DashboardTheme>(() => {
    if (typeof window === 'undefined') {
      return 'dark';
    }

    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === 'light' || storedTheme === 'dark') {
      return storedTheme;
    }

    return getMatchMedia('(prefers-color-scheme: dark)')?.matches ? 'dark' : 'light';
  });
  const [logoutConfirmArmed, setLogoutConfirmArmed] = useState(false);
  const logoutConfirmTimer = useRef<number | null>(null);

  const clearLogoutConfirmTimer = () => {
    if (logoutConfirmTimer.current === null) {
      return;
    }

    window.clearTimeout(logoutConfirmTimer.current);
    logoutConfirmTimer.current = null;
  };

  const cancelLogoutConfirm = () => {
    clearLogoutConfirmTimer();
    setLogoutConfirmArmed(false);
  };

  const handleLogoutClick = () => {
    if (logoutConfirmArmed) {
      cancelLogoutConfirm();
      logout();
      return;
    }

    clearLogoutConfirmTimer();
    setLogoutConfirmArmed(true);
    logoutConfirmTimer.current = window.setTimeout(() => {
      setLogoutConfirmArmed(false);
      logoutConfirmTimer.current = null;
    }, 4000);
  };

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => () => clearLogoutConfirmTimer(), []);

  return {
    cancelLogoutConfirm,
    handleLogoutClick,
    logoutConfirmArmed,
    setTheme,
    theme,
  };
}
