import React from 'react';
import { TimetableItem } from '../../types/api';
import {
  isValidData as validateData,
  getCorrectedValue,
  generateCourseTitle as generateTitle,
} from '../../utils/courseCorrections';
import { normalizeSemesterLabel } from '../../utils/semesterNormalization';

export type GroupedTimetable = Record<string, TimetableItem[]>;

export const getSectionColor = (index: number): React.CSSProperties => {
  // Golden-angle spacing keeps adjacent semester labels visually distinct,
  // even when a result contains more entries than a fixed palette supports.
  const hue = Math.round((index * 137.508 + 205) % 360);
  return {
    '--section-bg': `hsl(${hue} 70% 92%)`,
    '--section-border': `hsl(${hue} 58% 67%)`,
    '--section-text': `hsl(${hue} 52% 29%)`,
    '--section-dark-bg': `hsl(${hue} 28% 23%)`,
    '--section-dark-border': `hsl(${hue} 34% 42%)`,
    '--section-dark-text': `hsl(${hue} 65% 84%)`,
  } as React.CSSProperties;
};

export const parseTimeToMinutes = (timeStr: string): number => {
  if (!timeStr || timeStr === '-' || timeStr === 'null') {
    return 0;
  }

  const timeMatch = timeStr.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
  if (!timeMatch) {
    return 0;
  }

  let hours = parseInt(timeMatch[1], 10);
  const minutes = parseInt(timeMatch[2], 10);
  const period = timeMatch[3].toUpperCase();

  if (period === 'PM' && hours !== 12) {
    hours += 12;
  } else if (period === 'AM' && hours === 12) {
    hours = 0;
  }

  return hours * 60 + minutes;
};

export const getDisplayTime = (item: TimetableItem): string => {
  if (validateData(item.time)) {
    return item.time!;
  }

  return getCorrectedValue('time', item) || '-';
};

export const getDisplayRoom = (item: TimetableItem): string => {
  let room = item.room;

  if (room && room.toUpperCase() === 'TBD') {
    room = 'Online';
  }

  if (item.course === 'CSCL 2205') {
    return getCorrectedValue('room', item) || room || 'TBD';
  }

  if (validateData(room)) {
    return room!;
  }

  return getCorrectedValue('room', item) || 'TBD';
};

export const getDisplayCampus = (item: TimetableItem): string => {
  const campus = item.campus;

  if (validateData(campus)) {
    const campusString = campus!.trim();
    if (
      campusString.toLowerCase().includes('szabist') &&
      campusString.toLowerCase().includes('university')
    ) {
      return 'SZABIST University Campus';
    }

    return campusString;
  }

  return getCorrectedValue('campus', item) || '-';
};

export const getDisplayFaculty = (item: TimetableItem): string => {
  if (validateData(item.faculty)) {
    return item.faculty!;
  }

  return getCorrectedValue('faculty', item) || 'TBD';
};

export const getSemesterLabel = (item: TimetableItem): string =>
  normalizeSemesterLabel(item.semester_display || item.semester || item.semester_key);

export const getDisplayCourseTitle = (item: TimetableItem): string => {
  const title = validateData(item.course_title) ? item.course_title! : generateTitle(item);
  const courseIdentity = `${item.course || ''} ${item.course_code || ''}`;
  const isLab = /\blab\s*:/i.test(courseIdentity) || /\blab\b/i.test(String(item.course_type || ''));
  return isLab && !/\blab\s*$/i.test(title) ? `${title} Lab` : title;
};

export const getCourseCode = (item: TimetableItem): string => {
  const explicitCode = String(item.course_code || '').trim();
  if (explicitCode) return explicitCode;

  const course = String(item.course || '').trim();
  const extractedCode = course.match(/^([A-Z]{2,8}L?\s*[- ]?\s*\d{3,5}[A-Z]?)/i)?.[1];
  return extractedCode?.replace(/\s+/g, ' ').trim() || course || '-';
};

export const getCourseMeta = (item: TimetableItem): string => {
  const code = getCourseCode(item);
  const creditTuple = String(item.course || '').match(/\(\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*\)\s*$/)?.[0];
  return creditTuple ? `${code} · ${creditTuple.replace(/\s+/g, '')}` : code;
};

export const shouldHighlightRow = (item: TimetableItem): boolean => {
  const displayedTexts = [
    getDisplayCourseTitle(item),
    getDisplayFaculty(item),
    getDisplayRoom(item),
    getDisplayTime(item),
    getDisplayCampus(item),
    getSemesterLabel(item),
  ];

  return displayedTexts.some((text) => text.toLowerCase().includes('cancelled'));
};

export const renderHighlightedText = (text: string): React.ReactNode => {
  if (text.toLowerCase().includes('cancelled')) {
    return <span className="timetable-cancelled-text">{text}</span>;
  }

  return text;
};

export const groupAndSortData = (items: TimetableItem[]) => {
  const grouped = items.reduce((accumulator, item) => {
    const semester = getSemesterLabel(item) || 'Unassigned';
    if (!accumulator[semester]) {
      accumulator[semester] = [];
    }

    accumulator[semester].push(item);
    return accumulator;
  }, {} as GroupedTimetable);

  Object.keys(grouped).forEach((semester) => {
    grouped[semester].sort((left, right) => {
      const leftTime = parseTimeToMinutes(getDisplayTime(left));
      const rightTime = parseTimeToMinutes(getDisplayTime(right));

      if (leftTime === rightTime) {
        return getCourseCode(left).localeCompare(getCourseCode(right));
      }

      return leftTime - rightTime;
    });
  });

  return {
    grouped,
    sortedSemesters: Object.keys(grouped).sort(),
  };
};
