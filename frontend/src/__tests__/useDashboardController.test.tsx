import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { TimetableData } from '../types/api';

const apiMocks = vi.hoisted(() => ({
  getConfig: vi.fn(),
  getLatestTimetable: vi.fn(),
  getStatus: vi.fn(),
  initialize: vi.fn(),
  searchTimetable: vi.fn(),
}));

vi.mock('../services/api', () => ({
  BACKEND_WAKE_EVENT: 'backend-wake-state',
  apiService: apiMocks,
}));

import { useDashboardController } from '../features/dashboard/useDashboardController';

const makeSearchData = (query: string, answer: string, items: TimetableData['items'] = []): TimetableData => ({
  for_day: 'Monday',
  for_date: '',
  query: '',
  message_id: null,
  items,
  semesters: [],
  summary: {
    total_items: items.length,
    semester_breakdown: {},
    unique_courses: items.length,
    unique_faculty: 0,
  },
  search: {
    parser_version: 7,
    query,
    answer,
    intent: 'schedule',
    days: ['Monday'],
    entities: {},
    free_slots: {},
    recognized: items.length > 0,
  },
});

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  apiMocks.getConfig.mockResolvedValue({
    success: true,
    data: {
      gmail_query: '',
      semester_filter: [],
      schedule_time: '00:00',
      timezone: 'Asia/Karachi',
      max_results: 50,
    },
  });
});

test('a user search supersedes a slower background result restore', async () => {
  let resolveLatest!: (value: unknown) => void;
  apiMocks.getLatestTimetable.mockReturnValue(new Promise((resolve) => {
    resolveLatest = resolve;
  }));

  const query = 'BSSE7A timetable on Monday';
  const matchingItems = [{
    semester: 'BS(SE)-7A',
    course_title: 'Software Project Management',
    schedule_day: 'Monday',
  }];
  const currentResult = makeSearchData(query, 'Found 3 classes for BS(SE)-7A on Monday.', matchingItems);
  const staleResult = makeSearchData(
    'please solve something mysterious',
    "I couldn't identify a section, faculty member, course, class type, credit-hour value, or schedule scope in that question.",
  );
  apiMocks.searchTimetable.mockResolvedValue({
    success: true,
    data: currentResult,
    message: currentResult.search?.answer,
    timestamp: '2026-09-20T02:33:00',
  });

  const { result } = renderHook(() => useDashboardController({
    isAuthenticated: true,
    loading: false,
    logout: vi.fn(),
    user: { id: 'student', email: 'student@example.com' },
  }));

  await waitFor(() => expect(apiMocks.getLatestTimetable).toHaveBeenCalledOnce());

  await act(async () => {
    await result.current.runSmartSearch(query);
  });

  expect(apiMocks.searchTimetable).toHaveBeenCalledWith(query);
  expect(result.current.timetableData?.search?.query).toBe(query);
  expect(result.current.timetableData?.items).toHaveLength(1);

  await act(async () => {
    resolveLatest({ success: true, data: staleResult, timestamp: '2026-09-20T02:32:00' });
    await Promise.resolve();
  });

  await waitFor(() => expect(result.current.timetableData?.search?.query).toBe(query));
  expect(result.current.timetableData?.items).toHaveLength(1);

  act(() => result.current.clearSmartSearch());
  expect(result.current.searchQuery).toBe('');
  expect(result.current.timetableData).toBeNull();
});
