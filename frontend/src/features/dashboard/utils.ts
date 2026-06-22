import { ConfigData, TimetableData, TimetableItem } from '../../types/api';
import { normalizeSemesterKey, normalizeSemesterLabel } from '../../utils/semesterNormalization';

export const THEME_STORAGE_KEY = 'timetable-theme';
export const STATUS_TOAST_DURATION_MS = 3600;
export const STATUS_TOAST_FADE_MS = 280;

const getOrdinalSuffix = (day: number) => {
  if (day % 100 >= 11 && day % 100 <= 13) {
    return 'th';
  }

  switch (day % 10) {
    case 1:
      return 'st';
    case 2:
      return 'nd';
    case 3:
      return 'rd';
    default:
      return 'th';
  }
};

export const formatLastUpdate = (timestamp: string | null) => {
  if (!timestamp) {
    return { date: 'Never', time: 'Awaiting first sync' };
  }

  try {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
      return { date: 'Unknown', time: 'Unknown time' };
    }

    const day = date.getDate();
    const month = new Intl.DateTimeFormat('en-US', { month: 'long' }).format(date);
    const year = date.getFullYear();
    const time = date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });

    return {
      date: `${day}${getOrdinalSuffix(day)} of ${month}, ${year}`,
      time,
    };
  } catch {
    return { date: 'Unknown', time: 'Unknown time' };
  }
};

export const getMatchMedia = (query: string): MediaQueryList | null => {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return null;
  }

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

    const parts = rawSemester
      .split('/')
      .map((part) => part.trim())
      .filter(Boolean);

    if (parts.length < 2) {
      expandedItems.push(item);
      return;
    }

    parts.forEach((part) => {
      const normalizedDisplay = normalizeSemesterLabel(part);
      const normalizedKey = normalizeSemesterKey(part);

      expandedItems.push({
        ...item,
        semester_display: normalizedDisplay,
        semester: normalizedKey,
        semester_key: normalizedKey,
        section: normalizedDisplay,
        class_section: normalizedDisplay,
        semester_original: part,
      });
    });
  });

  return expandedItems;
};

export const getDetectedSemesters = (
  timetableData: TimetableData | null,
  configuredSemesters: string[],
) => {
  if (configuredSemesters.length > 0) {
    return configuredSemesters;
  }

  if (!timetableData?.items) {
    return [];
  }

  const semesters = new Set<string>();

  timetableData.items.forEach((item) => {
    const semesterLabel = normalizeSemesterLabel(
      item.semester_display ||
        item.semester ||
        item.semester_key ||
        item.section ||
        item.class_section,
    );

    if (semesterLabel) {
      semesters.add(semesterLabel);
    }
  });

  return Array.from(semesters);
};

const expandFilteredSocialSciences = (
  items: TimetableItem[],
  config: ConfigData | null,
) => {
  if (!config?.semester_filter || config.semester_filter.length < 2) {
    return items;
  }

  const expanded: TimetableItem[] = [];

  items.forEach((item) => {
    const department = (item.department || item.faculty || '').toString().toLowerCase();
    const isSocialSciences = department.includes('social') && department.includes('science');

    if (!isSocialSciences) {
      expanded.push(item);
      return;
    }

    const itemSemesterKey = normalizeSemesterKey(
      item.semester_key ||
        item.semester ||
        item.semester_display ||
        item.section ||
        item.class_section,
    );

    const matchingSemesters = config.semester_filter.filter((semester) => {
      const semesterKey = normalizeSemesterKey(semester);

      if (!semesterKey || !itemSemesterKey) {
        return false;
      }

      return (
        itemSemesterKey === semesterKey ||
        itemSemesterKey.endsWith(semesterKey) ||
        semesterKey.endsWith(itemSemesterKey)
      );
    });

    if (matchingSemesters.length === 0) {
      expanded.push(item);
      return;
    }

    matchingSemesters.forEach((semester) => {
      const normalizedDisplay = normalizeSemesterLabel(semester);
      const normalizedKey = normalizeSemesterKey(semester);

      expanded.push({
        ...item,
        semester_display: normalizedDisplay,
        semester: normalizedKey,
        semester_key: normalizedKey,
        section: normalizedDisplay,
        class_section: normalizedDisplay,
        semester_original: semester,
      });
    });
  });

  return expanded;
};

export const getFilteredTimetableItems = (
  timetableData: TimetableData | null,
  config: ConfigData | null,
) => {
  const sourceItems = timetableData?.items
    ? expandSocialSciencesSemesterItems(timetableData.items)
    : [];

  if (!timetableData?.items || !config?.semester_filter || config.semester_filter.length === 0) {
    return sourceItems;
  }

  const filteredItems = sourceItems.filter((item) => {
    const itemSemesterKey = normalizeSemesterKey(
      item.semester_key ||
        item.semester ||
        item.semester_display ||
        item.section ||
        item.class_section,
    );

    if (!itemSemesterKey) {
      return false;
    }

    return config.semester_filter.some((semester) => {
      const semesterKey = normalizeSemesterKey(semester);

      if (!semesterKey) {
        return false;
      }

      const directMatch =
        itemSemesterKey === semesterKey ||
        itemSemesterKey.endsWith(semesterKey) ||
        semesterKey.endsWith(itemSemesterKey);

      if (directMatch) {
        return true;
      }

      const department = (item.department || item.faculty || '').toString().toLowerCase();
      if (!department.includes('social') || !department.includes('science')) {
        return false;
      }

      const rawSemester = (
        item.semester_display ||
        item.semester ||
        item.semester_key ||
        item.section ||
        item.class_section ||
        ''
      ).toString();

      if (!rawSemester.includes('/')) {
        return false;
      }

      return rawSemester
        .split('/')
        .map((part: string) => part.trim())
        .filter(Boolean)
        .some((part: string) => {
          const partKey = normalizeSemesterKey(part);
          return Boolean(
            partKey &&
              (partKey === semesterKey ||
                partKey.endsWith(semesterKey) ||
                semesterKey.endsWith(partKey)),
          );
        });
    });
  });

  const expandedItems = expandFilteredSocialSciences(filteredItems, config);
  return expandedItems.length === 0 && sourceItems.length > 0 ? sourceItems : expandedItems;
};
