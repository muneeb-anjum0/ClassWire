import { afterEach, describe, expect, test, vi } from 'vitest';
import { ApiRequestError, apiService, getApiErrorMessage } from '../services/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('native API client', () => {
  test('sends authenticated bootstrap requests without a blocking probe', async () => {
    const payload = {
      success: true,
      user: { id: 'student', email: 'student@szabist-isb.pk' },
      timetable: null,
    };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiService.getBootstrap()).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:5001/api/bootstrap');
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: 'include', method: 'GET' });
  });

  test('serializes timetable searches as JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));
    vi.stubGlobal('fetch', fetchMock);

    await apiService.searchTimetable('BSSE7A on Monday');

    const options = fetchMock.mock.calls[0][1] as RequestInit;
    expect(options.method).toBe('POST');
    expect(options.body).toBe(JSON.stringify({ query: 'BSSE7A on Monday', force_refresh: false }));
    expect(options.headers).toMatchObject({ 'Content-Type': 'application/json' });
  });

  test('preserves API error messages for the interface', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: 'Authentication required' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    }));
    vi.stubGlobal('fetch', fetchMock);

    let caught: unknown;
    try {
      await apiService.getSession();
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiRequestError);
    expect(getApiErrorMessage(caught)).toBe('Authentication required');
  });
});
