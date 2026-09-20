import { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
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
  const SEARCH_PARSER_VERSION = 8;
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
  const [searchQuery, setSearchQuery] = useState('');
  const [isSmartResult, setIsSmartResult] = useState(false);
  const searchStorageKey = `classwire:v2:last-search:${user?.email || 'anonymous'}`;
  const timetableStorageKey = `classwire:v2:last-timetable:${user?.email || 'anonymous'}`;
  const bootstrapStarted = useRef(false);
  const dataRequestSequence = useRef(0);
  const searchInFlight = useRef(false);

  const readCachedTimetable = (): TimetableData | null => {
    try {
      const raw = window.localStorage.getItem(timetableStorageKey);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as TimetableData;
      if (!parsed || !Array.isArray(parsed.items)) return null;
      if (parsed.search && parsed.search.parser_version !== SEARCH_PARSER_VERSION) return null;
      return parsed;
    } catch {
      return null;
    }
  };

  const cacheTimetableLocally = (data: TimetableData) => {
    try {
      window.localStorage.setItem(timetableStorageKey, JSON.stringify(data));
    } catch (error) {
      console.warn('Could not cache timetable locally:', error);
    }
  };

  const readSavedSearch = (): TimetableData | null => {
    try {
      const saved = window.localStorage.getItem(timetableStorageKey);
      if (!saved) return null;
      const parsed = JSON.parse(saved) as TimetableData;
      return parsed?.search?.query && parsed.search.parser_version === SEARCH_PARSER_VERSION ? parsed : null;
    } catch {
      return null;
    }
  };

  const saveSearchLocally = (data: TimetableData) => {
    cacheTimetableLocally(data);
  };

  const configuredSemesters = useMemo(() => config?.semester_filter ?? [], [config]);
  const detectedSemesters = useMemo(
    () => getDetectedSemesters(timetableData, configuredSemesters),
    [configuredSemesters, timetableData],
  );
  const filteredItems = useMemo(
    () => isSmartResult ? (timetableData?.items || []) : getFilteredTimetableItems(timetableData, config),
    [config, isSmartResult, timetableData],
  );
  const activeFilterCount = config?.filter_mode === 'subjects'
    ? (config.subject_filters || []).length
    : config?.filter_mode === 'faculty'
      ? (config.faculty_filters || []).length
      : configuredSemesters.length;
  const noSemestersConfigured = activeFilterCount === 0;
  const lastUpdateDisplay = formatLastUpdate(lastUpdate);
  const loggedInLabel = ui.isMobileQuickActions
    ? user?.email?.split('@')[0] || 'User'
    : user?.email || 'Unknown user';
  const quickActionsToggleLabel = ui.isQuickActionsExpanded
    ? 'Collapse quick actions'
    : 'Expand quick actions';
  const semesterCount = activeFilterCount;
  const runButtonText = isScraperRunning
    ? 'Scraping...'
    : isSemesterUpdateRunning
      ? 'Updating...'
      : 'Run Scraper';
  const timetableDay = config?.timetable_day || 'Auto';

  const handleTimetableDayChange = async (day: string) => {
    const previousDay = timetableDay;
    setConfig((current) => current ? { ...current, timetable_day: day } : current);
    try {
      const response = await apiService.updateTimetableDay(day);
      if (!response.success) throw new Error(response.error || 'Failed to save timetable day');
      setTimetableData(null);
      showStatus('success', day === 'Auto' ? 'Timetable day set to automatic' : `Timetable search set to ${day}`);
    } catch (error) {
      setConfig((current) => current ? { ...current, timetable_day: previousDay } : current);
      showStatus('error', error instanceof Error ? error.message : 'Failed to save timetable day');
    }
  };

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

  const applySuccessfulTimetable = (
    data: TimetableData,
    timestamp?: string,
    message?: string,
    silent = false,
    status: 'success' | 'warning' = 'success',
  ) => {
    setTimetableData(data);
    cacheTimetableLocally(data);
    if (timestamp) {
      setLastUpdate(timestamp);
    }
    if (!silent) showStatus(status, message || 'Data loaded successfully');
  };

  const loadLatestTimetable = async (force = false, silent = false) => {
    if (operationInProgress && !force) {
      return;
    }

    const requestSequence = ++dataRequestSequence.current;
    try {
      if (!silent) {
        showStatus('warning', lastUpdate ? 'Loading cached data...' : 'Loading previous data...');
      }
      setIsLoading(true);
      setOperationInProgress(true);

      const response = await withInitializeRetry(
        () => apiService.getLatestTimetable(),
        'Network error when fetching timetable, retrying after autodetect',
      );
      if (requestSequence !== dataRequestSequence.current) return;

      if (response.success && response.data) {
        if (response.data.search?.query && response.data.search.parser_version !== SEARCH_PARSER_VERSION) {
          const staleQuery = response.data.search.query.trim();
          // Re-run the saved query against the already cached source. Parser
          // migrations must not trigger an expensive Gmail scrape.
          const refreshed = await apiService.searchTimetable(staleQuery);
          if (requestSequence !== dataRequestSequence.current) return;
          if (refreshed.success && refreshed.data) {
            setIsSmartResult(true);
            setSearchQuery(staleQuery);
            saveSearchLocally(refreshed.data);
            applySuccessfulTimetable(
              refreshed.data,
              refreshed.timestamp,
              'Updated your saved search',
              silent,
              refreshed.data.search?.recognized === false ? 'warning' : 'success',
            );
            return;
          }
        }
        const locallySavedSearch = readSavedSearch();
        const restoredData = response.data.search ? response.data : (locallySavedSearch || response.data);
        const restoredSearchQuery = restoredData.search?.query?.trim() || '';
        setIsSmartResult(Boolean(restoredData.search));
        setSearchQuery(restoredSearchQuery);
        applySuccessfulTimetable(
          restoredData,
          response.timestamp,
          restoredData.search ? 'Restored your last search' : response.cached ? 'Loaded cached data' : 'Data loaded successfully',
          silent,
        );
        return;
      }

      setTimetableData(null);
      showStatus('warning', 'No timetable data available. Try running a manual scrape.');
    } catch (error) {
      if (requestSequence !== dataRequestSequence.current) return;
      console.error('Error loading timetable:', error);
      setTimetableData(null);
      showStatus('error', 'Failed to load timetable data');
    } finally {
      if (requestSequence === dataRequestSequence.current) {
        setIsLoading(false);
        setOperationInProgress(false);
      }
    }
  };

  const runSmartSearch = async (query = searchQuery) => {
    const cleaned = query.trim();
    // A user search is allowed to supersede the background restore request.
    // searchInFlight is synchronous, unlike React state, so rapid submits
    // cannot create competing responses that overwrite one another.
    if (cleaned.length < 2 || searchInFlight.current || isScraperRunning) return;
    const requestSequence = ++dataRequestSequence.current;
    searchInFlight.current = true;
    try {
      setSearchQuery(cleaned);
      // Never leave an older answer visible while a different query is in
      // flight; that makes a correct input look as if it returned stale data.
      setTimetableData(null);
      setIsSmartResult(true);
      setIsScraperRunning(true);
      setOperationInProgress(true);
      showStatus('loading', 'Searching your timetable...');
      const response = await apiService.searchTimetable(cleaned);
      if (requestSequence !== dataRequestSequence.current) return;
      if (!response.success || !response.data) throw new Error(response.error || 'Search failed');
      if (response.data.search?.query?.trim() !== cleaned) {
        throw new Error('The search response did not match your question. Please try again.');
      }
      setIsSmartResult(true);
      saveSearchLocally(response.data);
      applySuccessfulTimetable(
        response.data,
        response.timestamp,
        response.message,
        false,
        response.data.search?.recognized === false ? 'warning' : 'success',
      );
    } catch (error) {
      if (requestSequence !== dataRequestSequence.current) return;
      setTimetableData(null);
      setIsSmartResult(true);
      const apiMessage = axios.isAxiosError(error)
        ? error.response?.data?.error || error.response?.data?.message
        : undefined;
      showStatus('error', apiMessage || (error instanceof Error ? error.message : 'Search failed'));
    } finally {
      searchInFlight.current = false;
      if (requestSequence === dataRequestSequence.current) {
        setIsScraperRunning(false);
        setOperationInProgress(false);
      }
    }
  };

  const clearSmartSearch = () => {
    if (isScraperRunning) return;
    dataRequestSequence.current += 1;
    setSearchQuery('');
    setTimetableData(null);
    setIsSmartResult(false);
    window.localStorage.removeItem(timetableStorageKey);
    statusToast.setStatus('idle');
    statusToast.setMessage('');
  };

  const executeScraper = async () => {
    const response = await apiService.runScraper();
    if (response.success && response.data) {
      window.localStorage.removeItem(searchStorageKey);
      setIsSmartResult(false);
      setSearchQuery('');
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

    if (!skipSemesterValidation && activeFilterCount === 0) {
      showStatus(
        'error',
        'No filters configured. Add semesters or subjects before running the parser.',
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

  const handleSaveDiscovery = async (mode: 'semesters' | 'subjects' | 'faculty', values: string[]) => {
    if (isSemesterUpdateRunning || operationInProgress) return;
    try {
      setIsSemesterUpdateRunning(true);
      setIsLoading(true);
      setOperationInProgress(true);
      showStatus('loading', 'Updating discovery filters...');
      const semesters = mode === 'semesters' ? values : (config?.semester_filter || []);
      const subjects = mode === 'subjects' ? values : (config?.subject_filters || []);
      const faculty = mode === 'faculty' ? values : (config?.faculty_filters || []);
      const response = await apiService.updateDiscovery(mode, semesters, subjects, faculty);
      if (!response.success) throw new Error(response.error || 'Failed to update filters');
      setConfig((current) => current ? { ...current, filter_mode: mode, semester_filter: semesters, subject_filters: subjects, faculty_filters: faculty } : current);
      setTimetableData(null);
      if (values.length === 0) {
        showStatus('warning', `Add at least one ${mode === 'subjects' ? 'subject' : mode === 'faculty' ? 'faculty' : 'semester'} filter.`);
        return;
      }
      showStatus('success', `Saved ${values.length} ${mode === 'subjects' ? 'subject' : mode === 'faculty' ? 'faculty' : 'semester'} filter(s). Running parser...`);
      window.setTimeout(() => runScraper({ skipSemesterValidation: true }), 500);
    } catch (error) {
      showStatus('error', error instanceof Error ? error.message : 'Failed to update filters');
    } finally {
      setIsSemesterUpdateRunning(false);
      setIsLoading(false);
      setOperationInProgress(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated || bootstrapStarted.current) {
      return;
    }
    bootstrapStarted.current = true;

    const cached = readCachedTimetable();
    if (cached) {
      setTimetableData(cached);
      setIsSmartResult(Boolean(cached.search));
      setSearchQuery(cached.search?.query?.trim() || '');
    }

    const bootstrap = async () => {
      await Promise.allSettled([
        loadConfig(),
        loadLatestTimetable(true, Boolean(cached)),
      ]);
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
    handleSaveDiscovery,
    handleSendTestEmail,
    handleToggleDailyEmail,
    handleTimetableDayChange,
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
    clearSmartSearch,
    runButtonText,
    runScraper,
    runSmartSearch,
    searchQuery,
    setSearchQuery,
    semesterCount,
    setIsQuickActionsExpanded: ui.setIsQuickActionsExpanded,
    setPersonalEmail,
    setShowSemesterManager,
    setTheme: ui.setTheme,
    showSemesterManager,
    status: statusToast.status,
    theme: ui.theme,
    timetableData,
    timetableDay,
    userEmail: user?.email,
  };
};
