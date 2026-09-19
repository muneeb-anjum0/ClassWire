import React, { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowUp,
  Clock3,
  LogOut,
  Moon,
  RefreshCw,
  Search,
  Sun,
  UserRound,
  X,
} from 'lucide-react';
import { TimetableData } from '../../types/api';
import { DashboardTheme } from './dashboardControllerTypes';
import {
  addRecentSearch,
  buildSmartSuggestions,
  parseRecentSearches,
  parseSuggestionHistory,
  rememberSuggestions,
  removeRecentSearch,
} from './smartSearchSuggestions';
import './smart-search.css';

type Props = {
  query: string;
  setQuery: (value: string) => void;
  onSearch: (query?: string) => void;
  loading: boolean;
  data: TimetableData | null;
  userEmail?: string;
  onLogout: () => void;
  logoutConfirmArmed: boolean;
  theme: DashboardTheme;
  onThemeChange: (theme: DashboardTheme) => void;
};

const WEEKDAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

export default function SmartSearch({
  query,
  setQuery,
  onSearch,
  loading,
  data,
  userEmail,
  onLogout,
  logoutConfirmArmed,
  theme,
  onThemeChange,
}: Props) {
  const [accountOpen, setAccountOpen] = useState(false);
  const [composerOpen, setComposerOpen] = useState(true);
  const [resultHidden, setResultHidden] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const accountRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);
  const suggestionHistoryRef = useRef<string[]>([]);
  const result = data?.search;
  const resultKey = `${result?.query || ''}|${result?.saved_at || ''}|${result?.answer || ''}`;
  const hasContent = Boolean(result || data?.items?.length);
  const availability = result?.faculty_availability || [];
  const recentStorageKey = useMemo(
    () => `classwire:v3:recent-searches:${(userEmail || 'anonymous').toLocaleLowerCase()}`,
    [userEmail],
  );
  const suggestionStorageKey = useMemo(
    () => `classwire:v3:suggestion-history:${(userEmail || 'anonymous').toLocaleLowerCase()}`,
    [userEmail],
  );

  const persistRecentSearches = useCallback((searches: string[]) => {
    setRecentSearches(searches);
    try {
      window.localStorage.setItem(recentStorageKey, JSON.stringify(searches));
    } catch (error) {
      console.warn('Could not save recent timetable searches:', error);
    }
  }, [recentStorageKey]);

  const rememberSearch = useCallback((search: string) => {
    setRecentSearches((current) => {
      const next = addRecentSearch(current, search);
      try {
        window.localStorage.setItem(recentStorageKey, JSON.stringify(next));
      } catch (error) {
        console.warn('Could not save recent timetable searches:', error);
      }
      return next;
    });
  }, [recentStorageKey]);

  const rotateSuggestions = useCallback((historyOverride?: string[]) => {
    let history = historyOverride || suggestionHistoryRef.current;
    let next = buildSmartSuggestions(data, 4, Math.random, history);

    if (next.length < 4) {
      history = history.slice(-12);
      next = buildSmartSuggestions(data, 4, Math.random, history);
    }

    const updatedHistory = rememberSuggestions(history, next);
    suggestionHistoryRef.current = updatedHistory;
    setSuggestions(next);
    try {
      window.localStorage.setItem(suggestionStorageKey, JSON.stringify(updatedHistory));
    } catch (error) {
      console.warn('Could not save suggestion rotation history:', error);
    }
  }, [data, suggestionStorageKey]);

  const runQuery = useCallback((search: string) => {
    const cleaned = search.trim();
    if (loading || cleaned.length < 2) return;
    setQuery(cleaned);
    rememberSearch(cleaned);
    setResultHidden(false);
    setComposerOpen(false);
    onSearch(cleaned);
  }, [loading, onSearch, rememberSearch, setQuery]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    runQuery(query);
  };

  const readableTime = (slot: string) => slot.replace(' – ', ' to ');
  const isAllDay = (freeSlots: string[]) => freeSlots.length === 1
    && freeSlots[0].replace(' – ', ' to ') === '8:00 AM to 9:30 PM';

  useEffect(() => {
    try {
      setRecentSearches(parseRecentSearches(window.localStorage.getItem(recentStorageKey)));
    } catch {
      setRecentSearches([]);
    }
  }, [recentStorageKey]);

  useEffect(() => {
    let storedHistory: string[] = [];
    try {
      storedHistory = parseSuggestionHistory(window.localStorage.getItem(suggestionStorageKey));
    } catch {
      storedHistory = [];
    }
    suggestionHistoryRef.current = storedHistory;
    rotateSuggestions(storedHistory);
  }, [rotateSuggestions, suggestionStorageKey]);

  useEffect(() => {
    setResultHidden(false);
    if (result) setComposerOpen(false);
  }, [resultKey]);

  useEffect(() => {
    const restoredQuery = result?.query?.trim();
    if (restoredQuery) rememberSearch(restoredQuery);
  }, [rememberSearch, result?.query]);

  useEffect(() => {
    if (!accountOpen && !composerOpen) return undefined;
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (accountOpen && !accountRef.current?.contains(target)) setAccountOpen(false);
      if (composerOpen && !composerRef.current?.contains(target)) setComposerOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setAccountOpen(false);
        setComposerOpen(false);
      }
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [accountOpen, composerOpen]);

  return <section className={`smart-search ${hasContent ? 'smart-search--compact' : 'smart-search--empty'}`}>
    <div className="smart-search__account" ref={accountRef}>
      <button
        type="button"
        className="smart-search__account-trigger"
        onClick={() => setAccountOpen((open) => !open)}
        aria-label="Open account menu"
        aria-expanded={accountOpen}
      ><UserRound aria-hidden="true" /></button>
      {accountOpen && <div className="smart-search__account-menu" role="menu">
        <div className="smart-search__account-email">
          <span>Signed in as</span>
          <strong>{userEmail || 'Google account'}</strong>
        </div>
        <button type="button" role="menuitem" onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}>
          {theme === 'dark' ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
        <button type="button" role="menuitem" className={logoutConfirmArmed ? 'is-danger' : ''} onClick={onLogout}>
          <LogOut aria-hidden="true" />
          {logoutConfirmArmed ? 'Click again to sign out' : 'Sign out'}
        </button>
      </div>}
    </div>

    {!hasContent && <header className="smart-search__intro">
      <h1>What’s on your schedule?</h1>
      <p>Ask about classes, faculty availability, courses, or sections.</p>
    </header>}

    <div className={`smart-search__composer ${composerOpen ? 'is-open' : ''}`} ref={composerRef}>
      <form onSubmit={submit} className="smart-search__form">
        <Search aria-hidden="true" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => setComposerOpen(true)}
          placeholder="Ask about your timetable"
          aria-label="Search timetable"
          aria-expanded={composerOpen}
          aria-controls="smart-search-discovery"
          autoComplete="off"
        />
        <button type="submit" disabled={loading || query.trim().length < 2} aria-label={loading ? 'Searching timetable' : 'Search timetable'}>
          {loading ? <span className="smart-search__loader" /> : <ArrowUp aria-hidden="true" />}
        </button>
      </form>

      {composerOpen && <div className="smart-search__discovery" id="smart-search-discovery">
        {recentSearches.length > 0 && <section className="smart-search__discovery-section">
          <header>
            <span>Recent</span>
            <button type="button" onClick={() => persistRecentSearches([])}>Clear all</button>
          </header>
          <div className="smart-search__recent-list">
            {recentSearches.map((search) => <div className="smart-search__recent" key={search}>
              <button type="button" className="smart-search__recent-query" onClick={() => runQuery(search)}>
                <Clock3 aria-hidden="true" />
                <span>{search}</span>
              </button>
              <button
                type="button"
                className="smart-search__remove-recent"
                onClick={() => persistRecentSearches(removeRecentSearch(recentSearches, search))}
                aria-label={`Remove ${search} from recent searches`}
              ><X aria-hidden="true" /></button>
            </div>)}
          </div>
        </section>}

        <section className="smart-search__discovery-section">
          <header>
            <span>Try asking</span>
            <button type="button" onClick={() => rotateSuggestions()}>
              <RefreshCw aria-hidden="true" />
              Refresh
            </button>
          </header>
          <div className="smart-search__suggestion-list">
            {suggestions.map((suggestion) => <button type="button" key={suggestion} onClick={() => runQuery(suggestion)}>
              <Search aria-hidden="true" />
              <span>{suggestion}</span>
            </button>)}
          </div>
        </section>
      </div>}
    </div>

    {result && resultHidden && <div className="smart-search__hidden-result" role="status">
      <span>Search result hidden</span>
      <button type="button" onClick={() => setResultHidden(false)}>Show</button>
    </div>}

    {result && !resultHidden && <div className="smart-search__answer">
      <div className="smart-search__answer-header">
        <div className="smart-search__answer-label">Search result</div>
        <button type="button" onClick={() => setResultHidden(true)} aria-label="Hide search result">
          <X aria-hidden="true" />
        </button>
      </div>
      {availability.length > 0 ? <div className="smart-search__availability">
        {availability.map(({ faculty, slots }) => <section className="smart-search__faculty" key={faculty}>
          <header>
            <h3>{faculty}</h3>
            <p>Free during university hours</p>
          </header>
          <div className="smart-search__days">
            {Object.entries(slots)
              .sort(([left], [right]) => WEEKDAY_ORDER.indexOf(left) - WEEKDAY_ORDER.indexOf(right))
              .map(([day, freeSlots]) => <div className="smart-search__day" key={`${faculty}-${day}`}>
                <strong>{day}</strong>
                {freeSlots.length > 0
                  ? <div className="smart-search__slots">
                    {isAllDay(freeSlots)
                      ? <span><b>All day</b><small>8:00 AM to 9:30 PM</small></span>
                      : freeSlots.map((slot, index) => <span key={slot}>{freeSlots.length > 1 && <i>{index + 1}</i>}{readableTime(slot)}</span>)}
                  </div>
                  : <span className="smart-search__none">No free time</span>}
              </div>)}
          </div>
        </section>)}
      </div> : <p>{result.answer}</p>}
    </div>}
  </section>;
}
