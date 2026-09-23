import { describe, expect, it } from 'vitest';
import { deleteLocalAccountData } from '../services/accountData';

describe('local account data cleanup', () => {
  it('removes user-scoped ClassWire data while preserving device preferences', async () => {
    const email = 'Student@SZABIST-ISB.PK';
    localStorage.setItem('classwire:v2:last-search:student@szabist-isb.pk', 'search');
    localStorage.setItem('classwire:v3:recent-searches:student@szabist-isb.pk', 'recent');
    localStorage.setItem('classwire:v3:suggestion-history:student@szabist-isb.pk', 'suggestions');
    localStorage.setItem('timetable-theme', 'dark');

    await deleteLocalAccountData(email);

    expect(localStorage.getItem('classwire:v2:last-search:student@szabist-isb.pk')).toBeNull();
    expect(localStorage.getItem('classwire:v3:recent-searches:student@szabist-isb.pk')).toBeNull();
    expect(localStorage.getItem('classwire:v3:suggestion-history:student@szabist-isb.pk')).toBeNull();
    expect(localStorage.getItem('timetable-theme')).toBe('dark');
  });
});
