import { expect, test } from 'vitest';
import { isSearchCacheFresh, requestedSourceDaysAreFresh } from '../services/timetableCache';
import { TimetableData } from '../types/api';

const resultAt = (savedAt: string, nextRefresh?: string): TimetableData => ({
  for_day: 'Monday',
  for_date: '2026-10-12',
  query: '',
  message_id: null,
  items: [],
  summary: {
    total_items: 0,
    semester_breakdown: {},
    unique_courses: 0,
    unique_faculty: 0,
  },
  source_cache: nextRefresh ? {
    tier: 'firestore',
    requested_days: ['Monday'],
    refreshed_at_by_day: { Monday: savedAt },
    next_refresh_at_by_day: { Monday: nextRefresh },
  } : undefined,
  search: {
    parser_version: 17,
    query: 'BSSE7A on Monday',
    saved_at: savedAt,
    answer: 'Found classes.',
    intent: 'schedule',
    days: ['Monday'],
    entities: {},
    free_slots: {},
  },
});

test('weekday search cache remains fresh until its exact server refresh boundary', () => {
  const refreshed = '2026-10-12T05:00:00Z';
  const expires = '2026-10-19T05:00:00Z';
  const result = resultAt(refreshed, expires);

  expect(isSearchCacheFresh(result, Date.parse('2026-10-19T04:59:59Z'))).toBe(true);
  expect(isSearchCacheFresh(result, Date.parse(expires))).toBe(false);
});

test('legacy cached results use the same seven-day maximum age', () => {
  const saved = '2026-10-12T05:00:00Z';
  const result = resultAt(saved);

  expect(isSearchCacheFresh(result, Date.parse('2026-10-19T04:59:59Z'))).toBe(true);
  expect(isSearchCacheFresh(result, Date.parse('2026-10-19T05:00:00Z'))).toBe(false);
});

test('all requested weekdays must be locally present and before their refresh boundary', () => {
  const source = {
    items: [],
    refreshed_at_by_day: {
      Monday: '2026-10-12T05:00:00Z',
      Tuesday: '2026-10-13T05:00:00Z',
    },
    next_refresh_at_by_day: {
      Monday: '2026-10-19T05:00:00Z',
      Tuesday: '2026-10-20T05:00:00Z',
    },
  };

  expect(requestedSourceDaysAreFresh(source, ['Monday'], Date.parse('2026-10-14T05:00:00Z'))).toBe(true);
  expect(requestedSourceDaysAreFresh(source, ['Monday', 'Wednesday'], Date.parse('2026-10-14T05:00:00Z'))).toBe(false);
  expect(requestedSourceDaysAreFresh(source, ['Monday'], Date.parse('2026-10-19T05:00:00Z'))).toBe(false);
});
