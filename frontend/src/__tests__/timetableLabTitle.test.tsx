import { describe, expect, it } from 'vitest';
import {
  getCourseMeta,
  getDisplayCourseTitle,
  sortTimetableItems,
} from '../components/TimetableTable/timetableTableUtils';

describe('timetable lab titles', () => {
  it('adds Lab to a parsed lab row title', () => {
    expect(getDisplayCourseTitle({
      course: 'SECL 3604 Lab: Software Construction and Development (0,1)',
      course_code: 'SECL 3604',
      course_title: 'Software Construction and Development',
    })).toBe('Software Construction and Development Lab');
  });

  it('does not change the lecture title', () => {
    expect(getDisplayCourseTitle({
      course: 'SEC 3604 Software Construction and Development (2,0)',
      course_code: 'SEC 3604',
      course_title: 'Software Construction and Development',
    })).toBe('Software Construction and Development');
  });

  it('does not append Lab twice', () => {
    expect(getDisplayCourseTitle({
      course: 'SECL 3604 Lab: Software Construction and Development Lab',
      course_title: 'Software Construction and Development Lab',
    })).toBe('Software Construction and Development Lab');
  });

  it('shows compact course metadata without repeating the title', () => {
    expect(getCourseMeta({
      course: 'SEC 3603 Software Project Management (3,0)',
      course_code: 'SEC 3603',
      course_title: 'Software Project Management',
    })).toBe('SEC 3603 · (3,0)');
  });

  it('extracts a compact code when legacy data has no course_code field', () => {
    expect(getCourseMeta({
      course: 'CSCL 1108 Lab: Introduction to Computer Science (0,1)',
      course_title: 'Introduction to Computer Science',
    })).toBe('CSCL 1108 · (0,1)');
  });
});

describe('timetable presentation order', () => {
  it('sorts merged semester results chronologically and leaves missing times last', () => {
    const items = [
      { course_code: 'SEC 3604', semester: 'BS(SE)-5A', time: '05:30 PM - 06:30 PM' },
      { course_code: 'SECL 3604', semester: 'BS(SE)-5B', time: '12:00 PM - 02:00 PM' },
      { course_code: 'SEC 3608', semester: 'BS(SE)-6A', time: '06:30 PM - 08:00 PM' },
      { course_code: 'SECL 3604', semester: 'BS(SE)-5A', time: '02:00 PM - 04:00 PM' },
      { course_code: 'SEC 3604', semester: 'BS(SE)-5B', time: '04:00 PM - 05:00 PM' },
      { course_code: 'TBD', semester: 'BS(SE)-6B', time: '-' },
    ];

    expect(sortTimetableItems(items).map((item) => item.time)).toEqual([
      '12:00 PM - 02:00 PM',
      '02:00 PM - 04:00 PM',
      '04:00 PM - 05:00 PM',
      '05:30 PM - 06:30 PM',
      '06:30 PM - 08:00 PM',
      '-',
    ]);
  });
});
