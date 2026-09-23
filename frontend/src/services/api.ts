import { ApiResponse, TimetableData, BootstrapData } from '../types/api';

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

const getBackendWakeMessage = () =>
  'Backend is waking up on Render. First request after inactivity can take about a minute.';

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
  return window.location.origin;
};

const selectedBaseUrl = () => {
  if (initializedApiUrl) return normalizeApiBaseUrl(initializedApiUrl);
  if (!isLocalNetworkHost(window.location.hostname)) {
    // Production uses Vercel's same-origin API proxy. This keeps the signed
    // session first-party in browsers that block third-party cookies.
    return normalizeApiBaseUrl(window.location.origin);
  }
  return normalizeApiBaseUrl(CONFIGURED_API_URL || getLocalApiBaseUrl());
};

const request = async <T>(
  path: string,
  options: { method?: string; body?: unknown; params?: Record<string, string> } = {},
): Promise<T> => {
  const query = options.params ? `?${new URLSearchParams(options.params)}` : '';
  const controller = new AbortController();
  const timeoutTimer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const wakeTimer = window.setTimeout(() => {
    emitBackendWakeState(true, getBackendWakeMessage());
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

export const apiService = {
  initialize: async (): Promise<string> => {
    if (initializedApiUrl) return initializedApiUrl;
    if (initializationPromise) return initializationPromise;

    initializationPromise = (async () => {
      if (!isLocalNetworkHost(window.location.hostname)) {
        initializedApiUrl = normalizeApiBaseUrl(window.location.origin);
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

  getGmailRedirectUrl: (frontendOrigin: string): string => {
    const params = new URLSearchParams({
      redirect: '1',
      frontend_origin: frontendOrigin,
    });
    return `${selectedBaseUrl()}/api/auth/gmail?${params}`;
  },
  exchangeAuthHandoff: (token: string) => request<{
    success: boolean;
    authenticated: true;
    user: { id: string; email: string };
  }>('/api/auth/handoff', { method: 'POST', body: { token } }),
  getBootstrap: () => request<BootstrapData>('/api/bootstrap'),
  deleteAccount: () => request<{ success: true; message: string }>('/api/account', { method: 'DELETE' }),
  logout: async (): Promise<void> => { await request('/api/auth/logout', { method: 'POST' }); },
  searchTimetable: (query: string, forceRefresh = false): Promise<ApiResponse<TimetableData>> =>
    request('/api/search', { method: 'POST', body: { query, force_refresh: forceRefresh } }),
  getLatestTimetable: () => request<ApiResponse<TimetableData>>('/api/timetable'),
};

export default apiService;
