import { TimetableItem } from '../../types/api';
import { normalizeSemesterKey, normalizeSemesterLabel } from '../../utils/semesterNormalization';

export const THEME_STORAGE_KEY = 'timetable-theme';
export const STATUS_TOAST_DURATION_MS = 3600;
export const STATUS_TOAST_FADE_MS = 280;

export const isSzabistIslamabadEmail = (email: string | null | undefined) =>
  typeof email === 'string' && /^[^@\s]+@szabist-isb\.pk$/i.test(email.trim());

export const getMatchMedia = (query: string): MediaQueryList | null => {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return null;
  return window.matchMedia(query);
};

export const expandSocialSciencesSemesterItems = (items: TimetableItem[]): TimetableItem[] => {
  const expandedItems: TimetableItem[] = [];

  items.forEach((item) => {
    const department = `${item.department || item.faculty || ''}`.toLowerCase();
    const rawSemester = `${
      item.semester_display ||
      item.semester ||
      item.semester_key ||
      item.section ||
      item.class_section ||
      ''
    }`;

    if (!department.includes('social') || !department.includes('science') || !rawSemester.includes('/')) {
      expandedItems.push(item);
      return;
    }

    const sections = rawSemester.split('/').map((part) => part.trim()).filter(Boolean);
    if (sections.length < 2) {
      expandedItems.push(item);
      return;
    }

    sections.forEach((section) => {
      const normalizedDisplay = normalizeSemesterLabel(section);
      const normalizedKey = normalizeSemesterKey(section);
      expandedItems.push({
        ...item,
        semester_display: normalizedDisplay,
        semester: normalizedKey,
        semester_key: normalizedKey,
        section: normalizedDisplay,
        class_section: normalizedDisplay,
        semester_original: section,
      });
    });
  });

  return expandedItems;
};
