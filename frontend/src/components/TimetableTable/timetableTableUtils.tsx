import React from 'react';
import { TimetableConflict, TimetableConflictClass, TimetableItem } from '../../types/api';
import { normalizeSemesterLabel } from '../../utils/semesterNormalization';

export type GroupedTimetable = Record<string, TimetableItem[]>;
export type ConflictMembership = Map<TimetableItem, { groupId: string; groupSize: number }>;
export type ConflictPosition = 'start' | 'middle' | 'end' | 'single';

const hasDisplayValue = (value: unknown): value is string => {
  if (typeof value !== 'string') return false;
  const normalized = value.trim().toLowerCase();
  return Boolean(normalized && normalized !== 'null' && normalized !== 'undefined');
};

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
    return Number.POSITIVE_INFINITY;
  }

  const timeMatch = timeStr.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
  if (!timeMatch) {
    return Number.POSITIVE_INFINITY;
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

export const compareTimetableItems = (left: TimetableItem, right: TimetableItem): number => {
  const timeDifference = parseTimeToMinutes(getDisplayTime(left)) - parseTimeToMinutes(getDisplayTime(right));
  if (timeDifference !== 0 && !Number.isNaN(timeDifference)) return timeDifference;

  const courseDifference = getCourseCode(left).localeCompare(getCourseCode(right));
  if (courseDifference !== 0) return courseDifference;

  const semesterDifference = getSemesterLabel(left).localeCompare(getSemesterLabel(right));
  if (semesterDifference !== 0) return semesterDifference;

  return getDisplayFaculty(left).localeCompare(getDisplayFaculty(right));
};

export const sortTimetableItems = (items: TimetableItem[]): TimetableItem[] =>
  [...items].sort(compareTimetableItems);

export const getDisplayTime = (item: TimetableItem): string => {
  return hasDisplayValue(item.time) ? item.time.trim() : '-';
};

export const getDisplayRoom = (item: TimetableItem): string => {
  return hasDisplayValue(item.room) ? item.room.trim() : 'TBD';
};

export const getDisplayCampus = (item: TimetableItem): string => {
  return hasDisplayValue(item.campus) ? item.campus.trim() : '-';
};

export const getDisplayFaculty = (item: TimetableItem): string => {
  return hasDisplayValue(item.faculty) ? item.faculty.trim() : 'TBD';
};

export const getSemesterLabel = (item: TimetableItem): string =>
  normalizeSemesterLabel(item.semester_display || item.semester || item.semester_key);

export const getDisplayCourseTitle = (item: TimetableItem): string => {
  const title = hasDisplayValue(item.course_title)
    ? item.course_title.trim()
    : hasDisplayValue(item.course)
      ? item.course.trim()
      : hasDisplayValue(item.course_code)
        ? item.course_code.trim()
        : 'Untitled course';
  const courseIdentity = `${item.course || ''} ${item.course_code || ''}`;
  const isLab = /\blab\s*:/i.test(courseIdentity) || /\blab\b/i.test(String(item.course_type || ''));
  return isLab && !/\blab\s*$/i.test(title) ? `${title} Lab` : title;
};

const normalizeConflictValue = (value: unknown): string =>
  String(value || '').trim().toLocaleLowerCase().replace(/[^a-z0-9]+/g, '');

const itemMatchesConflictClass = (
  item: TimetableItem,
  day: string,
  conflictClass: TimetableConflictClass,
): boolean => {
  const courses = [item.course_title, item.course].map(normalizeConflictValue).filter(Boolean);
  const sections = [item.semester_display, item.semester, item.section, item.class_section]
    .map(normalizeConflictValue)
    .filter(Boolean);
  return normalizeConflictValue(item.schedule_day) === normalizeConflictValue(day)
    && courses.includes(normalizeConflictValue(conflictClass.course))
    && sections.includes(normalizeConflictValue(conflictClass.section))
    && normalizeConflictValue(item.time) === normalizeConflictValue(conflictClass.time);
};

export const buildConflictMembership = (
  items: TimetableItem[],
  conflicts: TimetableConflict[] = [],
): ConflictMembership => {
  const parents = items.map((_, index) => index);
  const find = (index: number): number => {
    let current = index;
    while (parents[current] !== current) {
      parents[current] = parents[parents[current]];
      current = parents[current];
    }
    return current;
  };
  const join = (left: number, right: number) => {
    const leftRoot = find(left);
    const rightRoot = find(right);
    if (leftRoot !== rightRoot) parents[rightRoot] = leftRoot;
  };

  conflicts.forEach((conflict) => {
    const leftIndex = items.findIndex((item) => itemMatchesConflictClass(item, conflict.day, conflict.left));
    const rightIndex = items.findIndex((item, index) => (
      index !== leftIndex && itemMatchesConflictClass(item, conflict.day, conflict.right)
    ));
    if (leftIndex >= 0 && rightIndex >= 0) join(leftIndex, rightIndex);
  });

  const groups = new Map<number, number[]>();
  items.forEach((_, index) => {
    const root = find(index);
    const group = groups.get(root) || [];
    group.push(index);
    groups.set(root, group);
  });

  const membership: ConflictMembership = new Map();
  groups.forEach((indexes, root) => {
    if (indexes.length < 2) return;
    indexes.forEach((index) => membership.set(items[index], {
      groupId: `conflict-${root}`,
      groupSize: indexes.length,
    }));
  });
  return membership;
};

export const getConflictPosition = (
  items: TimetableItem[],
  index: number,
  membership: ConflictMembership,
): ConflictPosition | null => {
  const current = membership.get(items[index]);
  if (!current) return null;
  const previous = index > 0 ? membership.get(items[index - 1]) : undefined;
  const next = index < items.length - 1 ? membership.get(items[index + 1]) : undefined;
  const joinsPrevious = previous?.groupId === current.groupId;
  const joinsNext = next?.groupId === current.groupId;
  if (!joinsPrevious && !joinsNext) return 'single';
  if (!joinsPrevious) return 'start';
  if (!joinsNext) return 'end';
  return 'middle';
};

export const groupConflictingItems = (
  items: TimetableItem[],
  membership: ConflictMembership,
): TimetableItem[] => {
  const emittedGroups = new Set<string>();
  const arranged: TimetableItem[] = [];

  items.forEach((item) => {
    const conflict = membership.get(item);
    if (!conflict) {
      arranged.push(item);
      return;
    }
    if (emittedGroups.has(conflict.groupId)) return;

    emittedGroups.add(conflict.groupId);
    arranged.push(...items.filter(
      (candidate) => membership.get(candidate)?.groupId === conflict.groupId,
    ));
  });

  return arranged;
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
    grouped[semester].sort(compareTimetableItems);
  });

  return {
    grouped,
    sortedSemesters: Object.keys(grouped).sort(),
  };
};
