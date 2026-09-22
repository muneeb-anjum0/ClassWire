import { ApiResponse, TimetableData, ConfigData, StatusData, BootstrapData } from '../types/api';

export const BACKEND_WAKE_EVENT = 'backend-wake-state';
const BACKEND_WAKE_DELAY_MS = 4500;
const LOCAL_HEALTH_TIMEOUT_MS = 3000;
const REQUEST_TIMEOUT_MS = 120000;
const PRODUCTION_API_BASE_URL = 'https://timetable-wizard.onrender.com';
const LOCAL_API_BASE_URL = 'http://localhost:5001';
const CONFIGURED_API_URL = import.meta.env.VITE_API_URL;
let initializedApiUrl: string | null = null;
let initializationPromise: Promise<string> | null = null;

type ErrorPayload = { error?: string; message?: string };

export class ApiRequestError extends Error {
  readonly status: number;
  readonly data?: ErrorPayload;

  constructor(status: number, data?: ErrorPayload) {
    super(data?.error || data?.message || `Request failed with status ${status}`);
    this.name = 'ApiRequestError';
    this.status = status;
    this.data = data;
  }
}

export const getApiErrorMessage = (error: unknown): string | undefined =>
  error instanceof ApiRequestError
    ? error.data?.error || error.data?.message || error.message
    : undefined;

const getBackendWakeMessage = (path?: string) =>
  path?.includes('/api/scrape')
    ? 'Backend is waking up on Render. The parser will start as soon as the service is ready.'
    : 'Backend is waking up on Render. First request after inactivity can take about a minute.';

const emitBackendWakeState = (active: boolean, message?: string) => {
  window.dispatchEvent(new CustomEvent(BACKEND_WAKE_EVENT, { detail: { active, message } }));
};

const getBackendUnavailableMessage = (attemptedCandidates: string[]) => {
  const triedLocalBackend = attemptedCandidates.some(
    (candidate) => candidate.includes('localhost') || candidate.includes('127.0.0.1'),
  );
  return triedLocalBackend
    ? 'Unable to reach the backend. Start the local API server on port 5001 or set VITE_API_URL to a working backend URL.'
    : 'Unable to reach the backend. Check VITE_API_URL or make sure the deployed API is available.';
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

const selectedBaseUrl = () => normalizeApiBaseUrl(
  initializedApiUrl || CONFIGURED_API_URL || getLocalApiBaseUrl(),
);

const request = async <T>(
  path: string,
  options: { method?: string; body?: unknown; params?: Record<string, string> } = {},
): Promise<T> => {
  const query = options.params ? `?${new URLSearchParams(options.params)}` : '';
  const controller = new AbortController();
  const timeoutTimer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const wakeTimer = window.setTimeout(() => {
    emitBackendWakeState(true, getBackendWakeMessage(path));
  }, BACKEND_WAKE_DELAY_MS);

  try {
    const response = await fetch(`${selectedBaseUrl()}${path}${query}`, {
      method: options.method || 'GET',
      credentials: 'include',
      headers: options.body === undefined ? { Accept: 'application/json' } : {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    });
    const responseText = await response.text();
    let data: unknown = {};
    if (responseText) {
      try {
        data = JSON.parse(responseText);
      } catch {
        data = { error: responseText };
      }
    }
    if (!response.ok) throw new ApiRequestError(response.status, data as ErrorPayload);
    return data as T;
  } finally {
    window.clearTimeout(timeoutTimer);
    window.clearTimeout(wakeTimer);
    emitBackendWakeState(false);
  }
};

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

const withSettingsData = (responseData: any) => ({
  ...responseData,
  data: {
    personal_email: responseData.personal_email,
    daily_email_enabled: responseData.daily_email_enabled,
  },
});

export const apiService = {
  initialize: async (): Promise<string> => {
    if (initializedApiUrl) return initializedApiUrl;
    if (initializationPromise) return initializationPromise;

    initializationPromise = (async () => {
      if (!isLocalNetworkHost(window.location.hostname)) {
        initializedApiUrl = normalizeApiBaseUrl(CONFIGURED_API_URL || PRODUCTION_API_BASE_URL);
        return initializedApiUrl;
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
          initializedApiUrl = candidate;
          return candidate;
        }
        const controller = new AbortController();
        const timeoutTimer = window.setTimeout(() => controller.abort(), LOCAL_HEALTH_TIMEOUT_MS);
        try {
          const response = await fetch(`${candidate}/api/health`, {
            method: 'GET',
            mode: 'cors',
            signal: controller.signal,
          });
          if (response.ok) {
            initializedApiUrl = candidate;
            return candidate;
          }
        } catch (error) {
          lastError = error;
          await new Promise((resolve) => window.setTimeout(resolve, 200));
        } finally {
          window.clearTimeout(timeoutTimer);
        }
      }

      const message = getBackendUnavailableMessage(candidates);
      const detail = lastError instanceof Error ? ` ${lastError.message}` : '';
      throw new Error(`${message}${detail}`.trim());
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
      return new URL(selectedBaseUrl()).origin;
    } catch {
      return window.location.origin;
    }
  },

  getGmailAuthUrl: (frontendOrigin: string) => request<{ auth_url: string; state: string }>(
    '/api/auth/gmail',
    { params: { frontend_origin: frontendOrigin } },
  ),
  getSession: () => request<{ success: boolean; user: { id: string; email: string } }>('/api/auth/session'),
  getBootstrap: () => request<BootstrapData>('/api/bootstrap'),
  deleteAccount: async (): Promise<void> => { await request('/api/account', { method: 'DELETE' }); },
  logout: async (): Promise<void> => { await request('/api/auth/logout', { method: 'POST' }); },
  healthCheck: () => request<ApiResponse>('/api/health'),
  getConfig: async (): Promise<ApiResponse<ConfigData>> => ({
    success: true,
    data: await request<ConfigData>('/api/config'),
    timestamp: new Date().toISOString(),
  }),

  updateSemesters: async (semesters: string[]): Promise<ApiResponse> => {
    if (rateLimiter.shouldBlock('/api/config/semesters')) throw new Error('Please wait before updating semesters again');
    return request('/api/config/semesters', { method: 'POST', body: { semesters } });
  },
  updateDiscovery: (
    filterMode: 'semesters' | 'subjects' | 'faculty',
    semesters: string[],
    subjects: string[],
    faculty: string[],
  ): Promise<ApiResponse> => request('/api/config/discovery', {
    method: 'POST',
    body: { filter_mode: filterMode, semesters, subjects, faculty },
  }),
  updateTimetableDay: (timetableDay: string): Promise<ApiResponse<{ timetable_day: string }>> =>
    request('/api/config/timetable-day', { method: 'POST', body: { timetable_day: timetableDay } }),
  updatePersonalEmail: async (personalEmail: string): Promise<ApiResponse<{ personal_email: string; daily_email_enabled: boolean }>> => {
    if (rateLimiter.shouldBlock('/api/config/personal-email')) throw new Error('Please wait before updating your email again');
    return withSettingsData(await request('/api/config/personal-email', { method: 'POST', body: { personal_email: personalEmail } }));
  },
  updateDailyEmailEnabled: async (enabled: boolean): Promise<ApiResponse<{ personal_email: string; daily_email_enabled: boolean }>> => {
    if (rateLimiter.shouldBlock('/api/config/daily-email-enabled')) throw new Error('Please wait before updating daily email delivery again');
    return withSettingsData(await request('/api/config/daily-email-enabled', { method: 'POST', body: { daily_email_enabled: enabled } }));
  },
  sendTestTimetableEmail: async (): Promise<ApiResponse<{ items: number; personal_email: string }>> => {
    if (rateLimiter.shouldBlock('/api/automation/send-test-timetable-email')) throw new Error('Please wait before sending another email');
    return request('/api/automation/send-test-timetable-email', { method: 'POST' });
  },
  runScraper: async (): Promise<ApiResponse<TimetableData>> => {
    if (rateLimiter.shouldBlock('/api/scrape')) throw new Error('Please wait before running the scraper again');
    return request('/api/scrape', { method: 'POST' });
  },
  searchTimetable: (query: string, forceRefresh = false): Promise<ApiResponse<TimetableData>> =>
    request('/api/search', { method: 'POST', body: { query, force_refresh: forceRefresh } }),
  getLatestTimetable: () => request<ApiResponse<TimetableData>>('/api/timetable'),
  getStatus: () => request<ApiResponse<StatusData>>('/api/status'),
};

export default apiService;
