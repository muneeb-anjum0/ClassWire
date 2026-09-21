import axios, { AxiosResponse } from 'axios';
import { ApiResponse, TimetableData, ConfigData, StatusData } from '../types/api';

export const BACKEND_WAKE_EVENT = 'backend-wake-state';
const BACKEND_WAKE_DELAY_MS = 4500;
const LOCAL_HEALTH_TIMEOUT_MS = 3000;
const PRODUCTION_API_BASE_URL = 'https://timetable-wizard.onrender.com';
const LOCAL_API_BASE_URL = 'http://localhost:5001';
const CONFIGURED_API_URL = import.meta.env.VITE_API_URL;
let initializedApiUrl: string | null = null;
let initializationPromise: Promise<string> | null = null;

const getBackendWakeMessage = (url?: string) =>
  url?.includes('/api/scrape')
    ? 'Backend is waking up on Render. The parser will start as soon as the service is ready.'
    : 'Backend is waking up on Render. First request after inactivity can take about a minute.';

const emitBackendWakeState = (active: boolean, message?: string) => {
  window.dispatchEvent(new CustomEvent(BACKEND_WAKE_EVENT, { detail: { active, message } }));
};

const getBackendUnavailableMessage = (attemptedCandidates: string[]) => {
  const localCandidates = attemptedCandidates.filter(
    (candidate) => candidate.includes('localhost') || candidate.includes('127.0.0.1')
  );

  if (localCandidates.length > 0) {
    return 'Unable to reach the backend. Start the local API server on port 5001 or set VITE_API_URL to a working backend URL.';
  }

  return 'Unable to reach the backend. Check VITE_API_URL or make sure the deployed API is available.';
};

const normalizeApiBaseUrl = (url: string) => url.trim().replace(/\/+$/, '');

const isLocalNetworkHost = (hostname: string) =>
  hostname === 'localhost' ||
  hostname === '127.0.0.1' ||
  /^10\./.test(hostname) ||
  /^192\.168\./.test(hostname) ||
  /^172\.(?:1[6-9]|2\d|3[01])\./.test(hostname);

const getLocalApiBaseUrl = () => {
  const hostname = window.location.hostname;
  if (hostname === '127.0.0.1') return 'http://127.0.0.1:5001';
  if (hostname === 'localhost') return LOCAL_API_BASE_URL;
  if (isLocalNetworkHost(hostname)) return `http://${hostname}:5001`;
  return PRODUCTION_API_BASE_URL;
};

const api = axios.create({
  baseURL: CONFIGURED_API_URL || getLocalApiBaseUrl(),
  timeout: 120000,
  withCredentials: true,
});

const rateLimiter = {
  lastCalls: new Map<string, number>(),
  minInterval: 1000,

  shouldBlock(endpoint: string): boolean {
    const now = Date.now();
    const lastCall = this.lastCalls.get(endpoint);
    if (lastCall && now - lastCall < this.minInterval) return true;
    this.lastCalls.set(endpoint, now);
    return false;
  },
};

api.interceptors.request.use((config) => {
  const wakeTimer = window.setTimeout(() => {
    emitBackendWakeState(true, getBackendWakeMessage(config.url));
  }, BACKEND_WAKE_DELAY_MS);

  (config as any).metadata = { ...((config as any).metadata || {}), wakeTimer };

  return config;
});

api.interceptors.response.use(
  (response) => {
    const wakeTimer = (response.config as any).metadata?.wakeTimer;
    if (wakeTimer) {
      window.clearTimeout(wakeTimer);
      emitBackendWakeState(false);
    }
    return response;
  },
  (error) => {
    const wakeTimer = (error.config as any)?.metadata?.wakeTimer;
    if (wakeTimer) {
      window.clearTimeout(wakeTimer);
      emitBackendWakeState(false);
    }
    return Promise.reject(error);
  }
);

const withSettingsData = (responseData: any) => ({
  ...responseData,
  data: {
    personal_email: responseData.personal_email,
    daily_email_enabled: responseData.daily_email_enabled,
  },
});

export const apiService = {
  _axiosInstance: api,

  initialize: async (): Promise<string> => {
    if (initializedApiUrl) return initializedApiUrl;
    if (initializationPromise) return initializationPromise;

    initializationPromise = (async () => {
    const isLocalhost = isLocalNetworkHost(window.location.hostname);
    // Production already has one authoritative API origin. A blocking health
    // probe here used to wake Render and then make the real request wait for a
    // second network round trip. Select the known origin synchronously and let
    // the requested endpoint serve as the health check.
    if (!isLocalhost) {
      const productionUrl = normalizeApiBaseUrl(CONFIGURED_API_URL || PRODUCTION_API_BASE_URL);
      api.defaults.baseURL = productionUrl;
      initializedApiUrl = productionUrl;
      return productionUrl;
    }

    const candidates = Array.from(new Set([
      CONFIGURED_API_URL,
      getLocalApiBaseUrl(),
      PRODUCTION_API_BASE_URL,
    ].filter(Boolean).map((candidate) => normalizeApiBaseUrl(candidate as string))));
    let lastError: unknown = null;

    for (const candidate of candidates) {
      const isLocalCandidate = candidate.includes('localhost') || candidate.includes('127.0.0.1');
      if (!isLocalCandidate) {
        api.defaults.baseURL = candidate;
        initializedApiUrl = candidate;
        return candidate;
      }
      const controller = new AbortController();
      const timeoutTimer = window.setTimeout(() => controller.abort(), LOCAL_HEALTH_TIMEOUT_MS);
      const wakeTimer = isLocalCandidate
        ? undefined
        : window.setTimeout(() => {
            emitBackendWakeState(true, getBackendWakeMessage());
          }, BACKEND_WAKE_DELAY_MS);

      try {
        const res = await fetch(`${candidate}/api/health`, {
          method: 'GET',
          mode: 'cors',
          signal: controller.signal,
        });

        if (res.ok) {
          api.defaults.baseURL = candidate;
          initializedApiUrl = candidate;
          return candidate;
        }
      } catch (error) {
        lastError = error;
        await new Promise((resolve) => window.setTimeout(resolve, 200));
      } finally {
        window.clearTimeout(timeoutTimer);
        if (wakeTimer !== undefined) window.clearTimeout(wakeTimer);
        emitBackendWakeState(false);
      }
    }

    const errorMessage = getBackendUnavailableMessage(candidates);
    const causeMessage = lastError instanceof Error ? ` ${lastError.message}` : '';
    throw new Error(`${errorMessage}${causeMessage}`.trim());
    })();

    try {
      return await initializationPromise;
    } catch (error) {
      initializationPromise = null;
      throw error;
    }
  },

  getBaseOrigin: (): string => {
    try {
      if (api.defaults.baseURL) return new URL(api.defaults.baseURL).origin;
    } catch {
      return window.location.origin;
    }
    return window.location.origin;
  },

  getGmailAuthUrl: async (frontendOrigin: string): Promise<{ auth_url: string; state: string }> => {
    const response: AxiosResponse<{ auth_url: string; state: string }> = await api.get('/api/auth/gmail', {
      params: { frontend_origin: frontendOrigin },
    });
    return response.data;
  },

  getSession: async (): Promise<{ success: boolean; user: { id: string; email: string } }> => {
    const response = await api.get('/api/auth/session');
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/api/auth/logout');
  },

  healthCheck: async (): Promise<ApiResponse> => {
    const response: AxiosResponse<ApiResponse> = await api.get('/api/health');
    return response.data;
  },

  getConfig: async (): Promise<ApiResponse<ConfigData>> => {
    const response: AxiosResponse<ConfigData> = await api.get('/api/config');
    return { success: true, data: response.data, timestamp: new Date().toISOString() };
  },

  updateSemesters: async (semesters: string[]): Promise<ApiResponse> => {
    if (rateLimiter.shouldBlock('/api/config/semesters')) {
      throw new Error('Please wait before updating semesters again');
    }
    const response: AxiosResponse<ApiResponse> = await api.post('/api/config/semesters', { semesters });
    return response.data;
  },

  updateDiscovery: async (filterMode: 'semesters' | 'subjects' | 'faculty', semesters: string[], subjects: string[], faculty: string[]): Promise<ApiResponse> => {
    const response: AxiosResponse<ApiResponse> = await api.post('/api/config/discovery', {
      filter_mode: filterMode,
      semesters,
      subjects,
      faculty,
    });
    return response.data;
  },

  updateTimetableDay: async (timetableDay: string): Promise<ApiResponse<{ timetable_day: string }>> => {
    const response: AxiosResponse<ApiResponse<{ timetable_day: string }>> = await api.post('/api/config/timetable-day', {
      timetable_day: timetableDay,
    });
    return response.data;
  },

  updatePersonalEmail: async (personalEmail: string): Promise<ApiResponse<{ personal_email: string; daily_email_enabled: boolean }>> => {
    if (rateLimiter.shouldBlock('/api/config/personal-email')) {
      throw new Error('Please wait before updating your email again');
    }
    const response: AxiosResponse<any> = await api.post('/api/config/personal-email', { personal_email: personalEmail });
    return withSettingsData(response.data);
  },

  updateDailyEmailEnabled: async (enabled: boolean): Promise<ApiResponse<{ personal_email: string; daily_email_enabled: boolean }>> => {
    if (rateLimiter.shouldBlock('/api/config/daily-email-enabled')) {
      throw new Error('Please wait before updating daily email delivery again');
    }
    const response: AxiosResponse<any> = await api.post('/api/config/daily-email-enabled', { daily_email_enabled: enabled });
    return withSettingsData(response.data);
  },

  sendTestTimetableEmail: async (): Promise<ApiResponse<{ items: number; personal_email: string }>> => {
    if (rateLimiter.shouldBlock('/api/automation/send-test-timetable-email')) {
      throw new Error('Please wait before sending another email');
    }
    const response: AxiosResponse<ApiResponse<{ items: number; personal_email: string }>> = await api.post('/api/automation/send-test-timetable-email');
    return response.data;
  },

  runScraper: async (): Promise<ApiResponse<TimetableData>> => {
    if (rateLimiter.shouldBlock('/api/scrape')) {
      throw new Error('Please wait before running the scraper again');
    }
    const response: AxiosResponse<ApiResponse<TimetableData>> = await api.post('/api/scrape');
    return response.data;
  },

  searchTimetable: async (query: string, forceRefresh = false): Promise<ApiResponse<TimetableData>> => {
    const response: AxiosResponse<ApiResponse<TimetableData>> = await api.post('/api/search', { query, force_refresh: forceRefresh });
    return response.data;
  },

  getLatestTimetable: async (): Promise<ApiResponse<TimetableData>> => {
    const response: AxiosResponse<ApiResponse<TimetableData>> = await api.get('/api/timetable');
    return response.data;
  },

  getStatus: async (): Promise<ApiResponse<StatusData>> => {
    const response: AxiosResponse<ApiResponse<StatusData>> = await api.get('/api/status');
    return response.data;
  },
};

export default apiService;
