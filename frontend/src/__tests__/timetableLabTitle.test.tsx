import { describe, expect, it } from 'vitest';
import { getCourseMeta, getDisplayCourseTitle } from '../components/TimetableTable/timetableTableUtils';

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
