import { describe, expect, test } from 'vitest';
import { TimetableData } from '../types/api';
import {
  addRecentSearch,
  buildSmartSuggestions,
  parseRecentSearches,
  parseSuggestionHistory,
  rememberSuggestions,
  removeRecentSearch,
} from '../features/dashboard/smartSearchSuggestions';

describe('smart search discovery', () => {
  test('builds safe contextual suggestions from timetable data', () => {
    const data = {
      items: [{ faculty: 'Zainab Iftikhar Chaudhary', semester: 'BS(SE)-7A', course_title: 'Software Engineering' }],
    } as TimetableData;

    const suggestions = buildSmartSuggestions(data, 4, () => 0.25);

    expect(suggestions).toHaveLength(4);
    expect(suggestions.some((suggestion) => suggestion.includes('Zainab Iftikhar Chaudhary'))).toBe(true);
    expect(suggestions.some((suggestion) => suggestion.includes('BS(SE)-7A'))).toBe(true);
    expect(new Set(suggestions).size).toBe(suggestions.length);
  });

  test('rotates to an entirely new batch before reusing shown suggestions', () => {
    const first = buildSmartSuggestions(null, 4, () => 0.3);
    const second = buildSmartSuggestions(null, 4, () => 0.3, first);

    expect(second).toHaveLength(4);
    expect(second.filter((suggestion) => first.includes(suggestion))).toEqual([]);

    const history = rememberSuggestions(first, second);
    expect(parseSuggestionHistory(JSON.stringify(history))).toEqual(history);
  });

  test('does not repeat across seven fallback rotations', () => {
    let history: string[] = [];
    const shown = new Set<string>();

    for (let rotation = 0; rotation < 7; rotation += 1) {
      const batch = buildSmartSuggestions(null, 4, () => 0.42, history);
      expect(batch).toHaveLength(4);
      batch.forEach((suggestion) => {
        expect(shown.has(suggestion)).toBe(false);
        shown.add(suggestion);
      });
      history = rememberSuggestions(history, batch);
    }

    expect(shown.size).toBe(28);
  });

  test('keeps recent searches unique, removable, and resilient to invalid storage', () => {
    const searches = addRecentSearch(
      addRecentSearch(['When is Zainab free?'], 'Show BS(SE)-7A on Monday'),
      'when is zainab free?',
    );

    expect(searches).toEqual(['when is zainab free?', 'Show BS(SE)-7A on Monday']);
    expect(removeRecentSearch(searches, 'WHEN IS ZAINAB FREE?')).toEqual(['Show BS(SE)-7A on Monday']);
    expect(parseRecentSearches('{not-json')).toEqual([]);
  });
});
