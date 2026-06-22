import { DashboardTheme } from '../dashboardControllerTypes';

export type DailyEmailFieldsProps = {
  compact: boolean;
  dailyEmailEnabled: boolean;
  isDailyEmailToggleSaving: boolean;
  isOperationInProgress: boolean;
  isPersonalEmailSaving: boolean;
  isTestEmailSending: boolean;
  onSavePersonalEmail: () => void;
  onSendTestEmail: () => void;
  onSetPersonalEmail: (email: string) => void;
  onToggleDailyEmail: () => void;
  personalEmail: string;
};

export type QuickActionsPanelProps = {
  dailyEmailEnabled: boolean;
  isDailyEmailToggleSaving: boolean;
  isMobile: boolean;
  isOperationInProgress: boolean;
  isPersonalEmailSaving: boolean;
  isQuickActionsExpanded: boolean;
  isScraperRunning: boolean;
  isSemesterUpdateRunning: boolean;
  isTestEmailSending: boolean;
  lastUpdateDisplay: { date: string; time: string };
  loggedInLabel: string;
  logoutConfirmArmed: boolean;
  noSemestersConfigured: boolean;
  onCancelLogoutConfirm: () => void;
  onLogout: () => void;
  onRunScraper: () => void;
  onSavePersonalEmail: () => void;
  onSendTestEmail: () => void;
  onSetPersonalEmail: (email: string) => void;
  onShowSemesterManager: () => void;
  onThemeToggle: () => void;
  onToggleDailyEmail: () => void;
  onToggleQuickActions: () => void;
  personalEmail: string;
  quickActionsToggleLabel: string;
  runButtonText: string;
  semesterCount: number;
  theme: DashboardTheme;
  userEmail?: string;
};
