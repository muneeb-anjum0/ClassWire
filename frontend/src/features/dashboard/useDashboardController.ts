import { useEffect, useMemo, useRef, useState } from 'react';
import { apiService, getApiErrorMessage } from '../../services/api';
import {
  deleteTimetableCache,
  readTimetableCache,
  writeTimetableCache,
} from '../../services/timetableCache';
import { TimetableData } from '../../types/api';
import { withInitializeRetry } from './dashboardApi';
import { DashboardAuthState } from './dashboardControllerTypes';
import { useDashboardStatusToast } from './useDashboardStatusToast';
import { useDashboardUiState } from './useDashboardUiState';
import { expandSocialSciencesSemesterItems, isSzabistIslamabadEmail } from './utils';

const SEARCH_PARSER_VERSION = 13;

export const useDashboardController = ({
  bootstrap: authBootstrap,
  deleteAccount,
  isAuthenticated,
  loading,
  logout,
  user,
}: DashboardAuthState) => {
  const ui = useDashboardUiState(logout);
  const statusToast = useDashboardStatusToast();
  const showStatus = statusToast.showStatus;
  const [timetableData, setTimetableData] = useState<TimetableData | null>(null);
  const [isScraperRunning, setIsScraperRunning] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const hydratedUser = useRef<string | null>(null);
  const bootstrappedUser = useRef<string | null>(null);
  const dataRequestSequence = useRef(0);
  const searchInFlight = useRef(false);

  const filteredItems = useMemo(
    () => expandSocialSciencesSemesterItems(timetableData?.items || []),
    [timetableData],
  );
  const accountDomainWarning = isAuthenticated &&
    !loading &&
    !isSzabistIslamabadEmail(user?.email)
      ? 'You are signed in with a non-SZABIST account. Use your @szabist-isb.pk Google account to access SZABIST timetable emails.'
      : '';

  const readCachedTimetable = async (): Promise<TimetableData | null> => {
    const cached = await readTimetableCache(user?.email);
    if (cached?.search && cached.search.parser_version !== SEARCH_PARSER_VERSION) return null;
    return cached;
  };

  const readSavedSearch = async (): Promise<TimetableData | null> => {
    const cached = await readTimetableCache(user?.email);
    return cached?.search?.query && cached.search.parser_version === SEARCH_PARSER_VERSION
      ? cached
      : null;
  };

  const applySuccessfulTimetable = (
    data: TimetableData,
    message?: string,
    silent = false,
    status: 'success' | 'warning' = 'success',
  ) => {
    setTimetableData(data);
    void writeTimetableCache(user?.email, data);
    if (!silent) showStatus(status, message || 'Data loaded successfully');
  };

  const loadLatestTimetable = async (force = false, silent = false) => {
    if (operationInProgress && !force) return;

    const requestSequence = ++dataRequestSequence.current;
    try {
      if (!silent) showStatus('warning', 'Loading your saved timetable...');
      setOperationInProgress(true);
      const response = await withInitializeRetry(
        () => apiService.getLatestTimetable(),
        'Network error when fetching timetable, retrying after API initialization',
      );
      if (requestSequence !== dataRequestSequence.current) return;

      if (!response.success || !response.data) {
        if (!silent) showStatus('warning', 'Search for a class to load your timetable.');
        return;
      }

      if (response.data.search?.query && response.data.search.parser_version !== SEARCH_PARSER_VERSION) {
        const staleQuery = response.data.search.query.trim();
        const refreshed = await apiService.searchTimetable(staleQuery);
        if (requestSequence !== dataRequestSequence.current) return;
        if (refreshed.success && refreshed.data) {
          setSearchQuery(staleQuery);
          applySuccessfulTimetable(
            refreshed.data,
            'Updated your saved search',
            silent,
            refreshed.data.search?.recognized === false ? 'warning' : 'success',
          );
          return;
        }
      }

      const localSearch = await readSavedSearch();
      const restoredData = response.data.search ? response.data : (localSearch || response.data);
      setSearchQuery(restoredData.search?.query?.trim() || '');
      applySuccessfulTimetable(
        restoredData,
        restoredData.search ? 'Restored your last search' : 'Loaded your saved timetable',
        silent,
      );
    } catch (error) {
      if (requestSequence !== dataRequestSequence.current) return;
      console.error('Error loading timetable:', error);
      if (!silent) showStatus('error', 'Failed to load timetable data');
    } finally {
      if (requestSequence === dataRequestSequence.current) setOperationInProgress(false);
    }
  };

  const runSmartSearch = async (query = searchQuery) => {
    const cleaned = query.trim();
    if (cleaned.length < 2 || searchInFlight.current || isScraperRunning) return;

    const requestSequence = ++dataRequestSequence.current;
    searchInFlight.current = true;
    try {
      setSearchQuery(cleaned);
      setTimetableData(null);
      setIsScraperRunning(true);
      setOperationInProgress(true);
      showStatus('loading', 'Searching your timetable...');
      const response = await apiService.searchTimetable(cleaned);
      if (requestSequence !== dataRequestSequence.current) return;
      if (!response.success || !response.data) throw new Error(response.error || 'Search failed');
      if (response.data.search?.query?.trim() !== cleaned) {
        throw new Error('The search response did not match your question. Please try again.');
      }
      applySuccessfulTimetable(
        response.data,
        response.message,
        false,
        response.data.search?.recognized === false ? 'warning' : 'success',
      );
    } catch (error) {
      if (requestSequence !== dataRequestSequence.current) return;
      setTimetableData(null);
      const apiMessage = getApiErrorMessage(error);
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
    void deleteTimetableCache(user?.email);
    statusToast.setStatus('idle');
    statusToast.setMessage('');
  };

  const handleDeleteAccount = async () => {
    try {
      showStatus('loading', 'Deleting your ClassWire data...');
      await deleteAccount();
    } catch (error) {
      showStatus('error', error instanceof Error ? error.message : 'Could not delete account data');
      throw error;
    }
  };

  useEffect(() => {
    const userKey = user?.email?.trim().toLowerCase();
    if (!isAuthenticated || !userKey || hydratedUser.current === userKey) return;
    hydratedUser.current = userKey;

    void readCachedTimetable().then((cached) => {
      if (!cached || hydratedUser.current !== userKey) return;
      setTimetableData(cached);
      setSearchQuery(cached.search?.query?.trim() || '');
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.email]);

  useEffect(() => {
    const userKey = user?.email?.trim().toLowerCase();
    if (!isAuthenticated || loading || !userKey || bootstrappedUser.current === userKey) return;
    bootstrappedUser.current = userKey;

    void (async () => {
      const cached = await readCachedTimetable();
      if (authBootstrap?.user.email.toLowerCase() === userKey) {
        if (authBootstrap.timetable) {
          const localSearch = await readSavedSearch();
          const restoredData = authBootstrap.timetable.search
            ? authBootstrap.timetable
            : (localSearch || authBootstrap.timetable);
          setSearchQuery(restoredData.search?.query?.trim() || '');
          applySuccessfulTimetable(restoredData, undefined, true);
        }
        return;
      }
      await loadLatestTimetable(true, Boolean(cached));
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authBootstrap, isAuthenticated, loading, user?.email]);

  return {
    accountDomainWarning,
    cancelLogoutConfirm: ui.cancelLogoutConfirm,
    clearSmartSearch,
    deleteAccount: handleDeleteAccount,
    dismissStatus: statusToast.dismissStatus,
    filteredItems,
    handleLogoutClick: ui.handleLogoutClick,
    isBackendWaking: statusToast.isBackendWaking,
    isScraperRunning,
    isStatusToastClosing: statusToast.isStatusToastClosing,
    logoutConfirmArmed: ui.logoutConfirmArmed,
    message: statusToast.message,
    runSmartSearch,
    searchQuery,
    setSearchQuery,
    setTheme: ui.setTheme,
    status: statusToast.status,
    theme: ui.theme,
    timetableData,
    userEmail: user?.email,
  };
};
