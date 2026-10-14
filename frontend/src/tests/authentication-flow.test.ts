import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';
import vercelConfig from '../../vercel.json';
import { AuthProvider, parseAuthRedirect, useAuth } from '../context/AuthContext';

afterEach(() => {
  localStorage.clear();
  document.cookie = 'classwire_identity=; Path=/; Max-Age=0; SameSite=Lax';
  vi.unstubAllGlobals();
});

describe('private-browser authentication flow', () => {
  test('reads a successful single-use handoff from the URL fragment', () => {
    expect(parseAuthRedirect('#auth=success&handoff=one-time-token', '')).toEqual({
      status: 'success',
      handoff: 'one-time-token',
    });
  });

  test('retains an explicit OAuth failure without requiring a popup message', () => {
    expect(parseAuthRedirect('#auth=error', '')).toEqual({ status: 'error' });
  });

  test('proxies production API calls through the Vercel application origin', () => {
    expect(vercelConfig.rewrites[0]).toEqual({
      source: '/api/:path*',
      destination: 'https://timetable-wizard.onrender.com/api/:path*',
    });
  });

  test('restores a cached signed-in user without waking the backend', async () => {
    localStorage.setItem('classwire:v1:session-user', JSON.stringify({
      id: 'student',
      email: 'student@szabist-isb.pk',
    }));
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const Probe = () => {
      const auth = useAuth();
      return React.createElement('span', null, auth.loading ? 'loading' : auth.user?.email);
    };

    render(React.createElement(AuthProvider, null, React.createElement(Probe)));

    await waitFor(() => expect(screen.getByText('student@szabist-isb.pk')).toBeInTheDocument());
    expect(fetchMock).not.toHaveBeenCalled();
  });

  test('restores identity from the first-party cookie when mobile storage is missing', async () => {
    document.cookie = `classwire_identity=${encodeURIComponent(JSON.stringify({
      id: 'cookie-student',
      email: 'cookie.student@szabist-isb.pk',
    }))}; Path=/; SameSite=Lax`;
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const Probe = () => {
      const auth = useAuth();
      return React.createElement('span', null, auth.loading ? 'loading' : auth.user?.email);
    };

    render(React.createElement(AuthProvider, null, React.createElement(Probe)));

    await waitFor(() => expect(screen.getByText('cookie.student@szabist-isb.pk')).toBeInTheDocument());
    expect(fetchMock).not.toHaveBeenCalled();
  });

  test('logout clears browser identity through Vercel without contacting Render', async () => {
    localStorage.setItem('classwire:v1:session-user', JSON.stringify({
      id: 'student',
      email: 'student@szabist-isb.pk',
    }));
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const Probe = () => {
      const auth = useAuth();
      return React.createElement(
        'button',
        { type: 'button', onClick: auth.logout },
        auth.user?.email || 'signed out',
      );
    };

    render(React.createElement(AuthProvider, null, React.createElement(Probe)));
    const button = await screen.findByRole('button', { name: 'student@szabist-isb.pk' });
    button.click();

    await waitFor(() => expect(screen.getByRole('button', { name: 'signed out' })).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith('/logout-session.json', {
      method: 'GET',
      credentials: 'include',
      cache: 'no-store',
    });
    expect(localStorage.getItem('classwire:v1:explicitly-signed-out')).toBe('true');
  });
});
