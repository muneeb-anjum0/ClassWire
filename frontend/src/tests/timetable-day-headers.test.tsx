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

  it('marks online classes in both responsive schedule views', () => {
    const onlineClass = {
      ...classFor('Monday'),
      room: 'ONLINE',
    };
    const { container } = render(<TimetableTable items={[onlineClass]} />);

    expect(container.querySelector('.conversation-class')).toHaveClass('conversation-class--online');
    expect(container.querySelector('.tw-class-card')).toHaveClass('tw-class-card--online');
    expect(container.querySelector('.tw-room-pill')).toHaveClass('tw-room-pill--online');
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

  it('groups and marks clashing classes in both responsive views', () => {
    const earlyClash = {
      ...classFor('Monday'),
      semester_display: 'BS(SE)-7A',
      course_title: 'Software Project Management',
      time: '02:00 PM - 03:30 PM',
    };
    const unrelatedClass = {
      ...classFor('Monday'),
      semester_display: 'BS(SE)-5A',
      course_title: 'Short Elective',
      time: '02:30 PM - 03:00 PM',
    };
    const laterClash = {
      ...classFor('Monday'),
      semester_display: 'BS(SE)-6A',
      course_title: 'Software Quality Engineering and Testing',
      time: '03:00 PM - 04:00 PM',
    };
    const conflicts = [{
      day: 'Monday',
      overlap: '03:00 PM - 03:30 PM',
      left: {
        course: 'Software Project Management',
        section: 'BS(SE)-7A',
        time: '02:00 PM - 03:30 PM',
      },
      right: {
        course: 'Software Quality Engineering and Testing',
        section: 'BS(SE)-6A',
        time: '03:00 PM - 04:00 PM',
      },
    }];
    const { container } = render(
      <TimetableTable items={[earlyClash, unrelatedClass, laterClash]} conflicts={conflicts} />,
    );

    const desktopRows = Array.from(container.querySelectorAll('.conversation-class'));
    expect(desktopRows.map((row) => row.querySelector('strong')?.textContent)).toEqual([
      'Software Project Management',
      'Software Quality Engineering and Testing',
      'Short Elective',
    ]);
    expect(desktopRows[0]).toHaveClass('conversation-class--conflict-start');
    expect(desktopRows[1]).toHaveClass('conversation-class--conflict-end');
    expect(desktopRows[0].getAttribute('data-conflict-group')).toBe(
      desktopRows[1].getAttribute('data-conflict-group'),
    );
    expect(desktopRows[2]).not.toHaveClass('conversation-class--conflict');

    const mobileCards = Array.from(container.querySelectorAll('.tw-mobile-day .tw-class-card'));
    expect(mobileCards[0]).toHaveClass('tw-class-card--conflict-start');
    expect(mobileCards[1]).toHaveClass('tw-class-card--conflict-end');
    expect(mobileCards[2]).not.toHaveClass('tw-class-card--conflict');
  });
});
