import { useEffect, useMemo, useState } from 'react';
import { apiService } from '../../services/api';
import { ConfigData, TimetableData } from '../../types/api';
import {
  buildConfigAfterSemesterUpdate,
  withInitializeRetry,
} from './dashboardApi';
import { DashboardAuthState } from './dashboardControllerTypes';
import { useDashboardStatusToast } from './useDashboardStatusToast';
import { useDashboardEmailActions } from './useDashboardEmailActions';
import { useDashboardUiState } from './useDashboardUiState';
import {
  formatLastUpdate,
  getDetectedSemesters,
  getFilteredTimetableItems,
} from './utils';

export const useDashboardController = ({
  isAuthenticated,
  loading,
  logout,
  user,
}: DashboardAuthState) => {
  const ui = useDashboardUiState(logout);
  const statusToast = useDashboardStatusToast();
  const showStatus = statusToast.showStatus;
  const [timetableData, setTimetableData] = useState<TimetableData | null>(null);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [, setIsLoading] = useState(false);
  const [isScraperRunning, setIsScraperRunning] = useState(false);
  const [isSemesterUpdateRunning, setIsSemesterUpdateRunning] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [showSemesterManager, setShowSemesterManager] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState(false);

  const configuredSemesters = useMemo(() => config?.semester_filter ?? [], [config]);
  const detectedSemesters = useMemo(
    () => getDetectedSemesters(timetableData, configuredSemesters),
    [configuredSemesters, timetableData],
  );
  const filteredItems = useMemo(
    () => getFilteredTimetableItems(timetableData, config),
    [config, timetableData],
  );
  const noSemestersConfigured = detectedSemesters.length === 0;
  const lastUpdateDisplay = formatLastUpdate(lastUpdate);
  const loggedInLabel = ui.isMobileQuickActions
    ? user?.email?.split('@')[0] || 'User'
    : user?.email || 'Unknown user';
  const quickActionsToggleLabel = ui.isQuickActionsExpanded
    ? 'Collapse quick actions'
    : 'Expand quick actions';
  const semesterCount = detectedSemesters.length;
  const runButtonText = isScraperRunning
    ? 'Scraping...'
    : isSemesterUpdateRunning
      ? 'Updating...'
      : 'Run Scraper';

  const loadConfig = async (): Promise<ConfigData | null> => {
    try {
      const response = await apiService.getConfig();
      if (!response.success || !response.data) {
        return null;
      }

      setConfig(response.data);
      return response.data;
    } catch (error) {
      console.error('Error loading config:', error);
      return null;
    }
  };

  const checkStatus = async () => {
    try {
      const response = await withInitializeRetry(
        () => apiService.getStatus(),
        'Network error when fetching status, retrying after autodetect',
      );

      if (response.success && response.data) {
        setLastUpdate(response.data.last_update);
      }
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  const applySuccessfulTimetable = (data: TimetableData, timestamp?: string, message?: string) => {
    setTimetableData(data);
    if (timestamp) {
      setLastUpdate(timestamp);
    }
    showStatus('success', message || 'Data loaded successfully');
  };

  const loadLatestTimetable = async (force = false) => {
    if (operationInProgress && !force) {
      return;
    }

    try {
      showStatus(
        'warning',
        lastUpdate ? 'Loading cached data...' : 'Loading previous data...',
      );
      setIsLoading(true);
      setOperationInProgress(true);

      const response = await withInitializeRetry(
        () => apiService.getLatestTimetable(),
        'Network error when fetching timetable, retrying after autodetect',
      );

      if (response.success && response.data) {
        applySuccessfulTimetable(
          response.data,
          response.timestamp,
          response.cached ? 'Loaded cached data' : 'Data loaded successfully',
        );
        return;
      }

      setTimetableData(null);
      showStatus('warning', 'No timetable data available. Try running a manual scrape.');
    } catch (error) {
      console.error('Error loading timetable:', error);
      setTimetableData(null);
      showStatus('error', 'Failed to load timetable data');
    } finally {
      setIsLoading(false);
      setOperationInProgress(false);
    }
  };

  const executeScraper = async () => {
    const response = await apiService.runScraper();
    if (response.success && response.data) {
      applySuccessfulTimetable(
        response.data,
        response.timestamp,
        response.message || 'Parser completed successfully',
      );
      await checkStatus();
      return true;
    }

    showStatus('error', response.error || 'Parser failed');
    setTimetableData(null);
    return false;
  };

  const runScraper = async ({ skipSemesterValidation = false } = {}) => {
    if (isScraperRunning || operationInProgress) {
      return;
    }

    if (!skipSemesterValidation && (!config?.semester_filter || config.semester_filter.length === 0)) {
      showStatus(
        'error',
        'No semesters configured. Please add semesters before running the parser.',
      );
      return;
    }

    try {
      setIsScraperRunning(true);
      setIsLoading(true);
      setOperationInProgress(true);
      showStatus('loading', 'Running parser...');
      await executeScraper();
    } catch (error) {
      console.error('Error running scraper:', error);
      showStatus('error', 'Failed to run parser');
      setTimetableData(null);
    } finally {
      setIsScraperRunning(false);
      setIsLoading(false);
      setOperationInProgress(false);
    }
  };

  /* Email delivery actions live in useDashboardEmailActions. */
  const emailActions = useDashboardEmailActions({
    checkStatus,
    config,
    loadConfig,
    operationInProgress,
    setConfig,
    showStatus,
  });
  const {
    dailyEmailEnabled,
    handleSavePersonalEmail,
    handleSendTestEmail,
    handleToggleDailyEmail,
    isDailyEmailToggleSaving,
    isPersonalEmailSaving,
    isTestEmailSending,
    personalEmail,
    setPersonalEmail,
  } = emailActions;

  const handleSaveSemesters = async (newSemesters: string[]) => {
    if (isSemesterUpdateRunning || operationInProgress) {
      return;
    }

    try {
      setIsSemesterUpdateRunning(true);
      setIsLoading(true);
      setOperationInProgress(true);
      showStatus('loading', 'Updating semester settings...');

      const response = await apiService.updateSemesters(newSemesters);
      if (!response.success) {
        showStatus('error', response.error || 'Failed to update semesters');
        return;
      }

      setConfig((currentConfig) =>
        buildConfigAfterSemesterUpdate(currentConfig, newSemesters, personalEmail),
      );
      await loadConfig();
      setTimetableData(null);

      if (newSemesters.length === 0) {
        showStatus(
          'warning',
          'No semesters configured. Please add semesters to filter your schedule.',
        );
        return;
      }

      showStatus(
        'success',
        `Successfully updated ${newSemesters.length} semester(s). Running parser...`,
      );
      window.setTimeout(() => {
        runScraper({ skipSemesterValidation: true });
      }, 500);
    } catch (error) {
      console.error('Error updating semesters:', error);
      showStatus('error', 'Failed to update semesters');
    } finally {
      setIsSemesterUpdateRunning(false);
      setIsLoading(false);
      setOperationInProgress(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const bootstrap = async () => {
      await loadConfig();
      await checkStatus();
      await loadLatestTimetable();
    };

    bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  useEffect(() => {
    if (config && timetableData && noSemestersConfigured && !isScraperRunning && !operationInProgress) {
      showStatus(
        'warning',
        'No semesters configured. Please add semesters to filter and organize your schedule.',
      );
    }
  }, [config, noSemestersConfigured, operationInProgress, isScraperRunning, showStatus, timetableData]);

  return {
    authLoading: loading,
    cancelLogoutConfirm: ui.cancelLogoutConfirm,
    config,
    dailyEmailEnabled,
    detectedSemesters,
    dismissStatus: statusToast.dismissStatus,
    filteredItems,
    handleLogoutClick: ui.handleLogoutClick,
    handleSavePersonalEmail,
    handleSaveSemesters,
    handleSendTestEmail,
    handleToggleDailyEmail,
    isBackendWaking: statusToast.isBackendWaking,
    isDailyEmailToggleSaving,
    isMobileQuickActions: ui.isMobileQuickActions,
    isPersonalEmailSaving,
    isQuickActionsExpanded: ui.isQuickActionsExpanded,
    isScraperRunning,
    isSemesterUpdateRunning,
    isStatusToastClosing: statusToast.isStatusToastClosing,
    isTestEmailSending,
    lastUpdateDisplay,
    loggedInLabel,
    logoutConfirmArmed: ui.logoutConfirmArmed,
    message: statusToast.message,
    noSemestersConfigured,
    operationInProgress,
    personalEmail,
    quickActionsToggleLabel,
    runButtonText,
    runScraper,
    semesterCount,
    setIsQuickActionsExpanded: ui.setIsQuickActionsExpanded,
    setPersonalEmail,
    setShowSemesterManager,
    setTheme: ui.setTheme,
    showSemesterManager,
    status: statusToast.status,
    theme: ui.theme,
    timetableData,
    userEmail: user?.email,
  };
};
