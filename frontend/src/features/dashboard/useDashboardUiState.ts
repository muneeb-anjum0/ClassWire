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
  const [isMobileQuickActions, setIsMobileQuickActions] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }

    return getMatchMedia('(max-width: 768px)')?.matches ?? false;
  });
  const [isQuickActionsExpanded, setIsQuickActionsExpanded] = useState(() => {
    if (typeof window === 'undefined') {
      return true;
    }

    return !(getMatchMedia('(max-width: 768px)')?.matches ?? false);
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

  useEffect(() => {
    const mobileQuery = getMatchMedia('(max-width: 768px)');
    if (!mobileQuery) {
      return;
    }

    const handleChange = (event: MediaQueryListEvent) => {
      setIsMobileQuickActions(event.matches);
      setIsQuickActionsExpanded(!event.matches);
    };

    setIsMobileQuickActions(mobileQuery.matches);
    setIsQuickActionsExpanded(!mobileQuery.matches);

    if (mobileQuery.addEventListener) {
      mobileQuery.addEventListener('change', handleChange);
      return () => mobileQuery.removeEventListener('change', handleChange);
    }

    mobileQuery.addListener(handleChange);
    return () => mobileQuery.removeListener(handleChange);
  }, []);

  return {
    cancelLogoutConfirm,
    handleLogoutClick,
    isMobileQuickActions,
    isQuickActionsExpanded,
    logoutConfirmArmed,
    setIsQuickActionsExpanded,
    setTheme,
    theme,
  };
}
