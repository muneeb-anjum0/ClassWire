import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import SmartSearch from '../features/dashboard/SmartSearch';
import { TimetableData } from '../types/api';

const baseProps = {
  query: '',
  setQuery: vi.fn(),
  onSearch: vi.fn(),
  onClear: vi.fn(),
  loading: false,
  userEmail: 'student@example.com',
  onLogout: vi.fn(),
  logoutConfirmArmed: false,
  theme: 'light' as const,
  onThemeChange: vi.fn(),
};

test('recent searches can be reopened and removed', async () => {
  localStorage.setItem(
    'classwire:v3:recent-searches:student@example.com',
    JSON.stringify(['When is Zainab free?']),
  );
  const user = userEvent.setup();
  render(<SmartSearch {...baseProps} data={null} />);

  expect(await screen.findByText('When is Zainab free?')).toBeInTheDocument();
  await user.click(screen.getByLabelText('Remove When is Zainab free? from recent searches'));

  expect(screen.queryByText('When is Zainab free?')).not.toBeInTheDocument();
  expect(localStorage.getItem('classwire:v3:recent-searches:student@example.com')).toBe('[]');
});

test('a search answer can be hidden and restored without removing its data', async () => {
  const data = {
    for_day: 'Entire Week',
    for_date: '',
    query: 'When is Zainab free?',
    message_id: null,
    items: [],
    semesters: [],
    summary: {
      total_items: 0,
      semester_breakdown: {},
      unique_courses: 0,
      unique_faculty: 1,
    },
    search: {
      query: 'When is Zainab free?',
      answer: 'Zainab is free.',
      intent: 'free_time',
      days: ['Monday'],
      entities: {},
      free_slots: {},
      faculty_availability: [{
        faculty: 'Zainab Iftikhar Chaudhary',
        slots: { Monday: ['8:00 AM – 9:30 AM'] },
      }],
    },
  } satisfies TimetableData;
  const user = userEvent.setup();
  render(<SmartSearch {...baseProps} data={data} />);

  expect(screen.getByText('Zainab Iftikhar Chaudhary')).toBeInTheDocument();
  await user.click(screen.getByLabelText('Hide search result'));
  expect(screen.queryByText('Zainab Iftikhar Chaudhary')).not.toBeInTheDocument();
  expect(screen.getByText('Search result hidden')).toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: 'Show' }));
  expect(screen.getByText('Zainab Iftikhar Chaudhary')).toBeInTheDocument();
});

test('the composer clear button starts a new centered search', async () => {
  const onClear = vi.fn();
  const user = userEvent.setup();

  render(<SmartSearch {...baseProps} query="BSSE7A timetable Monday" onClear={onClear} data={null} />);

  await user.click(screen.getByRole('button', { name: 'Clear search and start over' }));

  expect(onClear).toHaveBeenCalledOnce();
});
