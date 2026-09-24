import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const dashboardState = vi.hoisted(() => ({ current: {} as Record<string, unknown> }));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({}),
}));

vi.mock('../features/dashboard/useDashboardController', () => ({
  useDashboardController: () => dashboardState.current,
}));

vi.mock('../features/dashboard/SmartSearch', () => ({
  default: () => <div data-testid="smart-search" />,
}));

vi.mock('../components/TimetableTable/TimetableTable', () => ({
  default: () => <div data-testid="timetable" />,
}));

vi.mock('../components/StatusIndicator/StatusIndicator', () => ({
  default: ({ status, message, onDismiss, tone }: { status: string; message: string; onDismiss?: () => void; tone?: string }) => (
    <div data-testid="schedule-status" data-status={status} data-tone={tone}>
      {message}
      {onDismiss && <button type="button" onClick={onDismiss}>Dismiss</button>}
    </div>
  ),
}));

import DashboardPage from '../features/dashboard/DashboardPage';

const itemFor = (scheduleDay: string) => ({
  schedule_day: scheduleDay,
  semester_display: 'BS(SE)-7A',
  course_title: `${scheduleDay} Class`,
});

function setDashboardState(overrides: Record<string, unknown> = {}) {
  const items = [itemFor('Monday')];
  dashboardState.current = {
    accountDomainWarning: '',
    clearSmartSearch: vi.fn(),
    deleteAccount: vi.fn(),
    dismissStatus: vi.fn(),
    filteredItems: items,
    handleLogoutClick: vi.fn(),
    isBackendWaking: false,
    isScraperRunning: false,
    isStatusToastClosing: false,
    logoutConfirmArmed: false,
    message: 'Schedule ready',
    runSmartSearch: vi.fn(),
    searchQuery: '',
    setSearchQuery: vi.fn(),
    setTheme: vi.fn(),
    status: 'success',
    theme: 'light',
    timetableData: {
      for_day: 'Monday',
      items,
      search: {
        conflict_count: 2,
        query_plan: { combination: 'union' },
      },
    },
    userEmail: 'student@example.com',
    ...overrides,
  };
}

describe('schedule feedback presentation', () => {
  beforeEach(() => setDashboardState());

  it('places status feedback above the separate conflict warning', () => {
    const { container } = render(<DashboardPage />);
    const panel = container.querySelector('.schedule-panel');
    const status = screen.getByTestId('schedule-status');
    const conflict = panel?.querySelector('.schedule-panel__conflicts');
    const feedbackRows = panel?.querySelectorAll('[data-testid="schedule-status"], .schedule-panel__conflicts');

    expect(panel).toContainElement(status);
    expect(Array.from(feedbackRows || []).map((element) => element.className)).toEqual([
      '',
      'schedule-panel__conflicts',
    ]);
    expect(status.nextElementSibling).toBe(conflict);
    expect(conflict?.nextElementSibling).toHaveClass('timetable-container');
  });

  it('keeps a status-only row directly adjacent to the timetable spacing boundary', () => {
    setDashboardState({
      timetableData: {
        for_day: 'Monday',
        items: [itemFor('Monday')],
        search: { conflict_count: 0 },
      },
    });
    const { container } = render(<DashboardPage />);

    expect(screen.getByTestId('schedule-status').nextElementSibling).toBe(
      container.querySelector('.timetable-container'),
    );
  });

  it('keeps a conflict-only row directly adjacent to the timetable spacing boundary', () => {
    setDashboardState({ status: 'idle' });
    const { container } = render(<DashboardPage />);
    const conflict = container.querySelector('.schedule-panel__conflicts');

    expect(conflict?.nextElementSibling).toBe(container.querySelector('.timetable-container'));
  });

  it('does not present parallel result rows as clashes outside a custom timetable', () => {
    setDashboardState({
      status: 'idle',
      timetableData: {
        for_day: 'Entire Week',
        items: [itemFor('Monday')],
        search: {
          conflict_count: 2,
          conflicts: [{ day: 'Monday' }],
          query_plan: { combination: 'intersection' },
        },
      },
    });
    const { container } = render(<DashboardPage />);

    expect(container.querySelector('.schedule-panel__conflicts')).not.toBeInTheDocument();
  });

  it('uses the amber wake treatment while Render is starting', () => {
    setDashboardState({ isBackendWaking: true, status: 'loading' });
    render(<DashboardPage />);

    expect(screen.getByTestId('schedule-status')).toHaveAttribute('data-tone', 'backend-wake');
  });

  it('stripes the schedule heading when one day has no separate day row', () => {
    const { container } = render(<DashboardPage />);

    expect(container.querySelector('.schedule-panel__header')).toHaveClass(
      'schedule-panel__header--striped',
    );
  });

  it('keeps multi-day schedule headings plain because each day has its own striped row', () => {
    const items = [itemFor('Monday'), itemFor('Wednesday')];
    setDashboardState({
      filteredItems: items,
      status: 'idle',
      timetableData: { for_day: 'Entire Week', items, search: {} },
    });
    const { container } = render(<DashboardPage />);

    expect(container.querySelector('.schedule-panel__header')).not.toHaveClass(
      'schedule-panel__header--striped',
    );
  });

  it('uses the same aligned status slot when no timetable is available', () => {
    setDashboardState({
      filteredItems: [],
      message: 'Search failed',
      status: 'error',
      timetableData: null,
    });
    const { container } = render(<DashboardPage />);

    expect(container.querySelector('.schedule-status-slot')).toContainElement(
      screen.getByTestId('schedule-status'),
    );
    expect(container.querySelector('.schedule-panel')).not.toBeInTheDocument();
  });

  it('shows a persistent error banner for an authenticated account outside the SZABIST domain', () => {
    setDashboardState({
      accountDomainWarning: 'Use your @szabist-isb.pk Google account.',
      status: 'idle',
    });
    render(<DashboardPage />);

    const warning = screen.getByTestId('schedule-status');
    expect(warning).toHaveAttribute('data-status', 'error');
    expect(warning).toHaveTextContent('Use your @szabist-isb.pk Google account.');
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument();
  });
});
