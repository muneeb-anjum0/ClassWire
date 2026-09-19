import { TimetableData, TimetableItem } from '../../types/api';

export const RECENT_SEARCH_LIMIT = 8;
export const SUGGESTION_HISTORY_LIMIT = 120;
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const clean = (value: unknown) => String(value || '').replace(/\s+/g, ' ').trim();

const distinct = (values: string[]) => {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = clean(value).toLocaleLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const FALLBACK_SUGGESTIONS = distinct([
  'Show the timetable for the entire week',
  'When are theory classes this week?',
  'Show all lab classes for the entire week',
  'When are FYP classes this week?',
  'Show all 3-credit-hour courses',
  'Show all 2-credit-hour theory courses',
  ...DAYS.flatMap((day) => [
    `Show every class on ${day}`,
    `Show every Software course on ${day}`,
    `When are theory classes on ${day}?`,
    `Show all lab classes on ${day}`,
  ]),
]);

const shuffled = <T,>(values: T[], random: () => number) => {
  const result = [...values];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const target = Math.floor(random() * (index + 1));
    [result[index], result[target]] = [result[target], result[index]];
  }
  return result;
};

const itemSection = (item: TimetableItem) => clean(
  item.semester_display || item.semester || item.class_section || item.section || item.semester_key,
);

const itemCourse = (item: TimetableItem) => clean(item.course_title || item.course);

export function buildSmartSuggestions(
  data: TimetableData | null,
  count = 4,
  random: () => number = Math.random,
  excluded: string[] = [],
): string[] {
  const items = data?.items || [];
  const faculty = distinct(items.map((item) => clean(item.faculty))).filter((name) => !/^unknown|tbd$/i.test(name)).slice(0, 32);
  const sections = distinct(items.map(itemSection)).filter((section) => !/^unknown|unassigned$/i.test(section)).slice(0, 32);
  const courses = distinct(items.map(itemCourse)).filter((course) => !/^unknown|untitled$/i.test(course)).slice(0, 32);
  const resultFaculty = distinct((data?.search?.faculty_availability || []).map(({ faculty: name }) => clean(name)));
  const excludedKeys = new Set(excluded.map((value) => clean(value).toLocaleLowerCase()));

  const contextualGroups = [
    resultFaculty.flatMap((name) => [
      `Show ${name}'s classes for the entire week`,
      ...DAYS.map((day) => `When is ${name} free on ${day}?`),
    ]),
    faculty.flatMap((name) => [
      `When is ${name} free this week?`,
      `Show ${name}'s classes for the entire week`,
      ...DAYS.flatMap((day) => [
        `When is ${name} free on ${day}?`,
        `Show ${name}'s classes on ${day}`,
      ]),
    ]),
    sections.flatMap((section) => [
      `Timetable for ${section} for the entire week`,
      ...DAYS.map((day) => `Show ${section} classes on ${day}`),
    ]),
    courses.flatMap((course) => [
      `When is ${course} taught this week?`,
      `Show every ${course} class`,
      ...DAYS.map((day) => `Show ${course} classes on ${day}`),
    ]),
  ].map(distinct).filter((group) => group.length > 0);

  const availableGroups = [...contextualGroups, FALLBACK_SUGGESTIONS]
    .map((group) => group.filter((suggestion) => !excludedKeys.has(suggestion.toLocaleLowerCase())))
    .filter((group) => group.length > 0);
  const primary = distinct(shuffled(availableGroups, random).map((group) => shuffled(group, random)[0]));
  const available = distinct(availableGroups.flatMap((group) => group));

  return distinct([
    ...shuffled(primary, random),
    ...shuffled(available, random),
  ]).slice(0, count);
}

export function parseSuggestionHistory(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? distinct(parsed.map(clean)).slice(-SUGGESTION_HISTORY_LIMIT)
      : [];
  } catch {
    return [];
  }
}

export function rememberSuggestions(history: string[], suggestions: string[]): string[] {
  const shownKeys = new Set(suggestions.map((suggestion) => clean(suggestion).toLocaleLowerCase()));
  return [
    ...history.filter((suggestion) => !shownKeys.has(clean(suggestion).toLocaleLowerCase())),
    ...suggestions,
  ].slice(-SUGGESTION_HISTORY_LIMIT);
}

export function parseRecentSearches(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? distinct(parsed.map(clean)).slice(0, RECENT_SEARCH_LIMIT)
      : [];
  } catch {
    return [];
  }
}

export function addRecentSearch(searches: string[], query: string): string[] {
  const value = clean(query);
  if (!value) return searches;
  return distinct([value, ...searches]).slice(0, RECENT_SEARCH_LIMIT);
}

export function removeRecentSearch(searches: string[], query: string): string[] {
  const target = clean(query).toLocaleLowerCase();
  return searches.filter((search) => clean(search).toLocaleLowerCase() !== target);
}
