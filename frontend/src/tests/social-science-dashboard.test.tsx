import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

if (typeof window.matchMedia === 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

const mockItems = vi.hoisted(() => [
    {
      row_number: 1,
      department: 'Social Sciences',
      program: 'BSSS & BS PSY',
      section: 'BSSS 1 / BS Psychology 1',
      semester_display: 'BSSS 1 / BS Psychology 1',
      semester: '',
      semester_key: '',
      class_section: 'BSSS 1 / BS Psychology 1',
      course: 'SS 1201 Introduction to Social Sciences',
      course_title: 'Introduction to Social Sciences',
      course_code: 'SS 1201',
      faculty: 'Abdul Hanan Sami',
      room: '204',
      time: '08:00 AM - 11:00 AM',
      campus: 'SZABIST University H-8/4 ISB Campus',
    },
    {
      row_number: 2,
      department: 'Social Sciences',
      program: 'BSSS & BS PSY',
      section: 'BSSS 1 / BS Psychology 1',
      semester_display: 'BSSS 1 / BS Psychology 1',
      semester: '',
      semester_key: '',
      class_section: 'BSSS 1 / BS Psychology 1',
      course: 'SS 1104 Introduction to Community Development and Philanthropy',
      course_title: 'Introduction to Community Development and Philanthropy',
      course_code: 'SS 1104',
      faculty: 'Abdul Hanan Sami',
      room: '301',
      time: '11:10 AM - 2:10 PM',
      campus: 'SZABIST University H-8/4 ISB Campus',
    },
  ]);

vi.mock('../services/api', () => {
  return {
    BACKEND_WAKE_EVENT: 'backend-wake-state',
    apiService: {
      initialize: vi.fn().mockResolvedValue('http://localhost:5000'),
      getBootstrap: vi.fn().mockResolvedValue({
        success: true,
        authenticated: true,
        user: { id: 'test-user', email: '2380223@szabist-isb.pk' },
        timetable: { items: mockItems },
      }),
      getLatestTimetable: vi.fn().mockResolvedValue({ success: true, data: { items: mockItems }, cached: true }),
      getGmailRedirectUrl: vi.fn(),
      exchangeAuthHandoff: vi.fn(),
      saveSearchHistory: vi.fn().mockResolvedValue({ success: true, searches: [] }),
    },
  };
});

beforeEach(() => {
  localStorage.setItem('user', JSON.stringify({ id: 'test-user', email: '2380223@szabist-isb.pk' }));
  localStorage.setItem('classwire:v2:last-timetable:2380223@szabist-isb.pk', JSON.stringify({
    for_day: 'Entire Week',
    for_date: '2026-10-14',
    query: '',
    message_id: null,
    items: mockItems,
    summary: { total_items: 2, semester_breakdown: {}, unique_courses: 2, unique_faculty: 1 },
  }));
});

test('App shows Social Sciences timetable in both semester sections', async () => {
  const App = (await import('../App')).default;
  render(<App />);

  // match semester headers flexibly (may render without spaces or split across nodes)
  await waitFor(
    () => expect(screen.getAllByText((content) => /BSSS\s*1/i.test(content)).length).toBeGreaterThanOrEqual(1),
    { timeout: 5000 },
  );
  await waitFor(
    () => expect(screen.getAllByText((content) => /BS\s*Psychology\s*1/i.test(content)).length).toBeGreaterThanOrEqual(1),
    { timeout: 5000 },
  );

  expect(screen.getAllByText(/Introduction to Social Sciences/i).length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText(/Introduction to Community Development and Philanthropy/i).length).toBeGreaterThanOrEqual(1);
});
