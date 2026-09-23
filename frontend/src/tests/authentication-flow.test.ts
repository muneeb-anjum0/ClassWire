import { describe, expect, test } from 'vitest';
import vercelConfig from '../../vercel.json';
import { parseAuthRedirect } from '../context/AuthContext';

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
});
