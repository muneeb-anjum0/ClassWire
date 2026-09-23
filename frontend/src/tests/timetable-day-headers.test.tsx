import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TimetableTable from '../components/TimetableTable/TimetableTable';

const classFor = (scheduleDay: string) => ({
  semester_display: 'BS(SE)-7A',
  course_title: `${scheduleDay} Course`,
  course_code: 'SEC 3603',
  schedule_day: scheduleDay,
  time: '02:00 PM - 03:30 PM',
  faculty: 'Faculty Member',
});

describe('timetable day headers', () => {
  it('renders full day-header rows in both responsive views for a multi-day timetable', () => {
    const { container } = render(
      <TimetableTable items={[classFor('Monday'), classFor('Wednesday')]} />,
    );

    expect(container.querySelectorAll('.conversation-day__header')).toHaveLength(2);
    expect(container.querySelectorAll('.tw-mobile-day-head')).toHaveLength(2);
  });

  it('does not add a redundant day-header row to a single-day timetable', () => {
    const { container } = render(<TimetableTable items={[classFor('Monday')]} />);

    expect(container.querySelector('.conversation-day__header')).not.toBeInTheDocument();
    expect(container.querySelector('.tw-mobile-day-head')).not.toBeInTheDocument();
  });

  it('shows a chronological mobile stream while retaining each class section', () => {
    const items = [
      {
        ...classFor('Monday'),
        semester_display: 'BS(SE)-7A',
        course_title: 'Late Class',
        time: '05:00 PM - 06:30 PM',
      },
      {
        ...classFor('Monday'),
        semester_display: 'BS(SE)-5B',
        course_title: 'Early Class',
        time: '02:00 PM - 03:00 PM',
      },
      {
        ...classFor('Monday'),
        semester_display: 'BS(SE)-6A',
        course_title: 'Middle Class',
        time: '03:30 PM - 05:00 PM',
      },
    ];
    const { container } = render(<TimetableTable items={items} />);
    const mobileCards = Array.from(container.querySelectorAll('.tw-mobile-day .tw-class-card'));

    expect(mobileCards.map((card) => card.querySelector('h4')?.textContent)).toEqual([
      'Early Class',
      'Middle Class',
      'Late Class',
    ]);
    expect(mobileCards.map((card) => card.querySelector('.tw-card-section')?.textContent)).toEqual([
      'BS(SE)-5B',
      'BS(SE)-6A',
      'BS(SE)-7A',
    ]);
  });
});
