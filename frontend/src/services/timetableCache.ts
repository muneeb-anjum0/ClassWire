import { TimetableData, TimetableItem } from '../types/api';

const DATABASE_NAME = 'classwire';
const STORE_NAME = 'timetables';
const SEARCH_STORE_NAME = 'search-results';
const SOURCE_STORE_NAME = 'timetable-sources';
const DATABASE_VERSION = 3;
const SEARCH_CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
const LEGACY_PREFIX = 'classwire:v2:last-timetable:';
const memoryCache = new Map<string, TimetableData>();
const searchMemoryCache = new Map<string, TimetableData>();
const sourceMemoryCache = new Map<string, CachedTimetableSource>();
let databasePromise: Promise<IDBDatabase | null> | null = null;

export interface CachedTimetableSource {
  items: TimetableItem[];
  parser_version?: number;
  refreshed_at_by_day: Record<string, string>;
  next_refresh_at_by_day: Record<string, string>;
}

const normalizeKey = (email?: string) => (email || 'anonymous').trim().toLowerCase();

const openDatabase = (): Promise<IDBDatabase | null> => {
  if (!('indexedDB' in window)) return Promise.resolve(null);
  if (databasePromise) return databasePromise;
  databasePromise = new Promise((resolve) => {
    const request = window.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE_NAME)) {
        request.result.createObjectStore(STORE_NAME);
      }
      if (!request.result.objectStoreNames.contains(SEARCH_STORE_NAME)) {
        request.result.createObjectStore(SEARCH_STORE_NAME);
      }
      if (!request.result.objectStoreNames.contains(SOURCE_STORE_NAME)) {
        request.result.createObjectStore(SOURCE_STORE_NAME);
      }
    };
    request.onsuccess = () => {
      request.result.onversionchange = () => {
        request.result.close();
        databasePromise = null;
      };
      resolve(request.result);
    };
    request.onerror = () => {
      databasePromise = null;
      resolve(null);
    };
  });
  return databasePromise;
};

const transact = async <T>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>,
  storeName = STORE_NAME,
) => {
  const database = await openDatabase();
  if (!database) return undefined;
  return new Promise<T | undefined>((resolve) => {
    const transaction = database.transaction(storeName, mode);
    const request = operation(transaction.objectStore(storeName));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(undefined);
    transaction.onerror = () => resolve(undefined);
    transaction.onabort = () => resolve(undefined);
  });
};

const validTimetable = (value: unknown): value is TimetableData =>
  Boolean(value && typeof value === 'object' && Array.isArray((value as TimetableData).items));

const normalizeQuery = (query: string) => query.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
const searchKey = (email: string | undefined, query: string) => `${normalizeKey(email)}\n${normalizeQuery(query)}`;

export const isSearchCacheFresh = (data: TimetableData, now = Date.now()): boolean => {
  const requestedDays = data.source_cache?.requested_days || [];
  const nextRefresh = data.source_cache?.next_refresh_at_by_day || {};
  if (requestedDays.length > 0 && requestedDays.every((day) => nextRefresh[day])) {
    return requestedDays.every((day) => {
      const expires = Date.parse(nextRefresh[day]);
      return Number.isFinite(expires) && expires > now;
    });
  }
  const savedAt = Date.parse(data.search?.saved_at || '');
  return Number.isFinite(savedAt) && now - savedAt < SEARCH_CACHE_MAX_AGE_MS;
};

const validSource = (value: unknown): value is CachedTimetableSource => Boolean(
  value && typeof value === 'object'
  && Array.isArray((value as CachedTimetableSource).items)
  && typeof (value as CachedTimetableSource).next_refresh_at_by_day === 'object',
);

export const requestedSourceDaysAreFresh = (
  source: CachedTimetableSource,
  requestedDays: string[],
  now = Date.now(),
): boolean => requestedDays.length > 0 && requestedDays.every((day) => {
  const expiry = Date.parse(source.next_refresh_at_by_day[day] || '');
  return Number.isFinite(expiry) && expiry > now;
});

export const readTimetableSourceCache = async (
  email?: string,
): Promise<CachedTimetableSource | null> => {
  const key = normalizeKey(email);
  const memoryResult = sourceMemoryCache.get(key);
  if (memoryResult) return memoryResult;
  const result = await transact<CachedTimetableSource>(
    'readonly',
    (store) => store.get(key),
    SOURCE_STORE_NAME,
  );
  if (!validSource(result)) return null;
  sourceMemoryCache.set(key, result);
  return result;
};

export const writeTimetableSourceCache = async (
  email: string | undefined,
  data: TimetableData,
): Promise<void> => {
  const metadata = data.source_cache;
  if (!metadata?.source_items || !Array.isArray(metadata.source_items)) return;
  const source: CachedTimetableSource = {
    items: metadata.source_items,
    parser_version: metadata.parser_version,
    refreshed_at_by_day: metadata.refreshed_at_by_day || {},
    next_refresh_at_by_day: metadata.next_refresh_at_by_day || {},
  };
  const key = normalizeKey(email);
  sourceMemoryCache.set(key, source);
  await transact<IDBValidKey>('readwrite', (store) => store.put(source, key), SOURCE_STORE_NAME);
};

export const readSearchResultCache = async (
  email: string | undefined,
  query: string,
): Promise<TimetableData | null> => {
  const key = searchKey(email, query);
  const memoryResult = searchMemoryCache.get(key);
  if (memoryResult && isSearchCacheFresh(memoryResult)) return memoryResult;
  const result = await transact<TimetableData>(
    'readonly',
    (store) => store.get(key),
    SEARCH_STORE_NAME,
  );
  if (validTimetable(result) && isSearchCacheFresh(result)) {
    searchMemoryCache.set(key, result);
    return result;
  }
  return null;
};

export const readTimetableCache = async (email?: string): Promise<TimetableData | null> => {
  const key = normalizeKey(email);
  const inMemory = memoryCache.get(key);
  if (inMemory) return inMemory;
  const fromDatabase = await transact<TimetableData>('readonly', (store) => store.get(key));
  if (validTimetable(fromDatabase)) {
    memoryCache.set(key, fromDatabase);
    return fromDatabase;
  }

  // One-time migration from the old synchronous cache.
  try {
    const legacyKey = `${LEGACY_PREFIX}${key}`;
    const raw = window.localStorage.getItem(legacyKey);
    const parsed = raw ? JSON.parse(raw) : null;
    if (validTimetable(parsed)) {
      await writeTimetableCache(email, parsed);
      if ('indexedDB' in window) window.localStorage.removeItem(legacyKey);
      return parsed;
    }
  } catch {
    // A corrupt or unavailable legacy cache should never block startup.
  }
  return null;
};

export const writeTimetableCache = async (email: string | undefined, data: TimetableData): Promise<void> => {
  const key = normalizeKey(email);
  memoryCache.set(key, data);
  const query = data.search?.query?.trim();
  if (query) searchMemoryCache.set(searchKey(email, query), data);
  await writeTimetableSourceCache(email, data);
  const persistedData = data.source_cache?.source_items
    ? {
      ...data,
      source_cache: { ...data.source_cache, source_items: undefined },
    }
    : data;
  const persistedKey = await transact<IDBValidKey>('readwrite', (store) => store.put(persistedData, key));
  if (persistedKey === undefined) {
    try {
      window.localStorage.setItem(`${LEGACY_PREFIX}${key}`, JSON.stringify(persistedData));
    } catch {
      // Keep the in-memory cache when browser persistence is unavailable.
    }
    return;
  }
  try {
    window.localStorage.removeItem(`${LEGACY_PREFIX}${key}`);
  } catch {
    // Ignore cleanup failures.
  }
  if (query) {
    await transact<IDBValidKey>(
      'readwrite',
      (store) => store.put(persistedData, searchKey(email, query)),
      SEARCH_STORE_NAME,
    );
  }
};

export const deleteTimetableCache = async (
  email?: string,
  includeSearchResults = true,
): Promise<void> => {
  const key = normalizeKey(email);
  memoryCache.delete(key);
  if (includeSearchResults) {
    sourceMemoryCache.delete(key);
    for (const cachedKey of searchMemoryCache.keys()) {
      if (cachedKey.startsWith(`${key}\n`)) searchMemoryCache.delete(cachedKey);
    }
  }
  await transact('readwrite', (store) => store.delete(key));
  const database = await openDatabase();
  if (database && includeSearchResults) {
    await transact('readwrite', (store) => store.delete(key), SOURCE_STORE_NAME);
  }
  if (database && includeSearchResults) {
    await new Promise<void>((resolve) => {
      const transaction = database.transaction(SEARCH_STORE_NAME, 'readwrite');
      const request = transaction.objectStore(SEARCH_STORE_NAME).openCursor();
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        if (String(cursor.key).startsWith(`${key}\n`)) cursor.delete();
        cursor.continue();
      };
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => resolve();
      transaction.onabort = () => resolve();
    });
  }
  try {
    window.localStorage.removeItem(`${LEGACY_PREFIX}${key}`);
  } catch {
    // Ignore unavailable storage.
  }
};
