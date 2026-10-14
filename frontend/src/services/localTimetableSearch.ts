import { CachedTimetableSource } from './timetableCache';
import { TimetableData, TimetableItem } from '../types/api';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const DAY_ALIASES: Record<string, string[]> = {
  Monday: ['monday', 'mon'], Tuesday: ['tuesday', 'tue', 'tues'],
  Wednesday: ['wednesday', 'wed', 'weds'], Thursday: ['thursday', 'thu', 'thur', 'thurs'],
  Friday: ['friday', 'fri'], Saturday: ['saturday', 'sat'],
};
const DAY_START = 8 * 60;
const DAY_END = 21 * 60 + 30;

const compact = (value: unknown) => String(value || '').toLocaleLowerCase().replace(/[^a-z0-9]+/g, '');
const words = (value: unknown) => String(value || '').toLocaleLowerCase().match(/[a-z0-9]+/g) || [];
const sectionOf = (item: TimetableItem) => String(
  item.semester_display || item.semester || item.section || '',
);
const courseOf = (item: TimetableItem) => String(item.course_title || item.course || '');
const codeOf = (item: TimetableItem) => String(item.course_code || '');
const dayOf = (item: TimetableItem) => String(item.schedule_day || item.day || '');

export const parseLocalQueryDays = (query: string, now = new Date()): string[] => {
  const tokens = new Set(words(query));
  const explicit = DAYS.filter((day) => DAY_ALIASES[day].some((alias) => tokens.has(alias)));
  if (explicit.length) return explicit;
  if (/\b(?:entire|all|whole)\s+week\b/i.test(query)) return DAYS;
  const relative = /\btomorrow\b/i.test(query) ? 1 : /\byesterday\b/i.test(query) ? -1 : /\btoday\b/i.test(query) ? 0 : null;
  if (relative !== null) {
    const karachiDate = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Karachi' }));
    karachiDate.setDate(karachiDate.getDate() + relative);
    const day = karachiDate.toLocaleDateString('en-US', { weekday: 'long' });
    return DAYS.includes(day) ? [day] : [];
  }
  return DAYS;
};

const uniqueLabels = (items: TimetableItem[], getter: (item: TimetableItem) => string) =>
  Array.from(new Set(items.map(getter).map((value) => value.trim()).filter(Boolean)));

const labelsNamedInQuery = (query: string, labels: string[]) => {
  const normalizedQuery = compact(query);
  return labels.filter((label) => compact(label).length >= 2 && normalizedQuery.includes(compact(label)));
};

const facultyNamedInQuery = (query: string, faculty: string[]) => {
  const exact = labelsNamedInQuery(query, faculty);
  if (exact.length) return exact;
  const queryTokens = new Set(words(query).filter((word) => !['sir', 'maam', 'mam', 'madam', 'dr', 'prof'].includes(word)));
  const tokenMatches = faculty.filter((name) => {
    const meaningful = words(name).filter((word) => word.length >= 4 && !['sheikh', 'muhammad', 'syed'].includes(word));
    return meaningful.some((word) => queryTokens.has(word));
  });
  return tokenMatches.length === 1 ? tokenMatches : [];
};

const timeToMinutes = (value: string) => {
  const match = value.trim().match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
  if (!match) return null;
  let hour = Number(match[1]) % 12;
  if (match[3].toUpperCase() === 'PM') hour += 12;
  return hour * 60 + Number(match[2]);
};

const minuteLabel = (minutes: number) => {
  const hour24 = Math.floor(minutes / 60);
  const minute = minutes % 60;
  const period = hour24 >= 12 ? 'PM' : 'AM';
  const hour = hour24 % 12 || 12;
  return `${hour}:${String(minute).padStart(2, '0')} ${period}`;
};

const freeSlots = (items: TimetableItem[], days: string[]) => Object.fromEntries(days.map((day) => {
  const busy = items
    .filter((item) => dayOf(item) === day)
    .map((item) => String(item.time || item.schedule_time || '').split(/\s*(?:-|–|to)\s*/i))
    .map(([start, end]) => [timeToMinutes(start || ''), timeToMinutes(end || '')] as const)
    .filter((interval): interval is readonly [number, number] => interval[0] !== null && interval[1] !== null)
    .sort((left, right) => left[0] - right[0]);
  const merged: Array<[number, number]> = [];
  for (const [start, end] of busy) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  const slots: string[] = [];
  let cursor = DAY_START;
  for (const [start, end] of merged) {
    if (start > cursor) slots.push(`${minuteLabel(cursor)} to ${minuteLabel(start)}`);
    cursor = Math.max(cursor, end);
  }
  if (cursor < DAY_END) slots.push(`${minuteLabel(cursor)} to ${minuteLabel(DAY_END)}`);
  return [day, slots];
}));

const summaryFor = (items: TimetableItem[]) => {
  const semesterBreakdown: Record<string, number> = {};
  items.forEach((item) => {
    const semester = sectionOf(item) || 'Unknown';
    semesterBreakdown[semester] = (semesterBreakdown[semester] || 0) + 1;
  });
  return {
    total_items: items.length,
    semester_breakdown: semesterBreakdown,
    unique_courses: new Set(items.map((item) => codeOf(item) || courseOf(item))).size,
    unique_faculty: new Set(items.map((item) => String(item.faculty || '')).filter(Boolean)).size,
  };
};

export const searchCachedTimetable = (
  query: string,
  source: CachedTimetableSource,
  parserVersion: number,
  now = new Date(),
): TimetableData => {
  const days = parseLocalQueryDays(query, now);
  const dayItems = source.items.filter((item) => days.includes(dayOf(item)));
  const sections = labelsNamedInQuery(query, uniqueLabels(source.items, sectionOf));
  const courses = labelsNamedInQuery(query, uniqueLabels(source.items, courseOf));
  const codes = labelsNamedInQuery(query, uniqueLabels(source.items, codeOf));
  const faculty = facultyNamedInQuery(query, uniqueLabels(source.items, (item) => String(item.faculty || '')));
  const wantsFreeTime = /\b(?:free|available|availability|open\s+slots?|office\s+hours?|gaps?)\b/i.test(query);
  const wantsTheory = /\btheory\b/i.test(query);
  const wantsLab = /\b(?:lab|labs|laboratory|laboratories)\b/i.test(query);
  const normalizedQuery = compact(query);
  const positionedSections = sections
    .map((section) => ({ section, index: normalizedQuery.indexOf(compact(section)) }))
    .filter(({ index }) => index >= 0)
    .sort((left, right) => left.index - right.index);
  const positionedCourses = courses
    .map((course) => ({ course, index: normalizedQuery.indexOf(compact(course)) }))
    .filter(({ index }) => index >= 0)
    .sort((left, right) => left.index - right.index);
  const firstCourseIndex = positionedCourses[0]?.index ?? Number.POSITIVE_INFINITY;
  const baseSection = positionedSections.find(({ index }) => index < firstCourseIndex)?.section
    || (courses.length === 0 ? positionedSections[0]?.section : undefined);
  const pairedSectionByCourse = new Map<string, string>();
  positionedCourses.forEach(({ course, index }, courseIndex) => {
    const nextCourseIndex = positionedCourses[courseIndex + 1]?.index ?? Number.POSITIVE_INFINITY;
    const paired = positionedSections.find((section) => section.index > index && section.index < nextCourseIndex);
    if (paired) pairedSectionByCourse.set(course, paired.section);
  });
  const exclusionStart = query.search(/\b(?:except|excluding|without|do\s+not\s+take|don't\s+take|dont\s+take)\b/i);
  const exclusionText = exclusionStart >= 0
    ? compact(query.slice(exclusionStart).split(/,|;|\b(?:and\s+(?:i\s+am\s+)?taking|plus|but)\b/i)[0])
    : '';
  const excludedCourses = courses.filter((course) => exclusionText.includes(compact(course)));
  const selected = dayItems.filter((item) => {
    const itemSection = sectionOf(item);
    const itemCourse = courseOf(item);
    const sectionMatch = sections.length > 0 && sections.includes(itemSection);
    const courseMatch = courses.length > 0 && courses.includes(itemCourse);
    const codeMatch = codes.length > 0 && codes.includes(codeOf(item));
    const facultyMatch = faculty.length > 0 && faculty.includes(String(item.faculty || ''));
    const hasEntity = sections.length + courses.length + codes.length + faculty.length > 0;
    const pairedSection = pairedSectionByCourse.get(itemCourse);
    const customScheduleMatch = Boolean(
      (baseSection && itemSection === baseSection && !excludedCourses.includes(itemCourse))
      || (courseMatch && !excludedCourses.includes(itemCourse) && (!pairedSection || pairedSection === itemSection))
      || codeMatch,
    );
    if (hasEntity && !(facultyMatch || (sections.length && courses.length
      ? customScheduleMatch
      : sectionMatch || courseMatch || codeMatch))) return false;
    const creditText = `${item.course || ''} ${item.course_title || ''} ${item.full_text || ''}`;
    const classTypeApplies = courses.length === 0 || courseMatch;
    if (classTypeApplies && wantsTheory && !/\(\s*[23](?:\.0)?\s*,\s*0(?:\.0)?\s*\)/.test(creditText)) return false;
    if (classTypeApplies && wantsLab && !/\(\s*0(?:\.0)?\s*,\s*1(?:\.0)?\s*\)/.test(creditText)) return false;
    return true;
  });
  const availability = wantsFreeTime && faculty.length
    ? faculty.map((name) => ({
      faculty: name,
      slots: freeSlots(source.items.filter((item) => String(item.faculty || '') === name), days),
    }))
    : undefined;
  const answer = availability
    ? `${faculty.join(' and ')} free during university hours.`
    : `Found ${selected.length} ${selected.length === 1 ? 'class' : 'classes'} for your query.`;
  return {
    for_day: days.length === DAYS.length ? 'Entire Week' : days.join(' / '),
    for_date: now.toISOString().slice(0, 10),
    query,
    message_id: null,
    items: selected,
    summary: summaryFor(selected),
    source_cache: {
      tier: 'browser',
      requested_days: days,
      refreshed_at_by_day: source.refreshed_at_by_day,
      next_refresh_at_by_day: source.next_refresh_at_by_day,
      parser_version: source.parser_version,
      source_items: source.items,
    },
    search: {
      parser_version: parserVersion,
      query,
      saved_at: now.toISOString(),
      recognized: Boolean(selected.length || availability?.length),
      answer,
      intent: availability ? 'free_time' : 'schedule',
      days,
      entities: { sections, courses, codes, faculty },
      free_slots: availability?.[0]?.slots || {},
      faculty_availability: availability,
    },
  };
};
