export type DashboardTheme = 'light' | 'dark';

export type DashboardStatus = 'idle' | 'loading' | 'success' | 'error' | 'warning';

export type DashboardAuthState = {
  bootstrap: import('../../types/api').BootstrapData | null;
  deleteAccount: () => Promise<void>;
  isAuthenticated: boolean;
  loading: boolean;
  logout: () => void;
  user: { id: string; email: string } | null;
};
