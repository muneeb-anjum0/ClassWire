import { TimetableData } from '../types/api';

const DATABASE_NAME = 'classwire';
const STORE_NAME = 'timetables';
const DATABASE_VERSION = 1;
const LEGACY_PREFIX = 'classwire:v2:last-timetable:';
const memoryCache = new Map<string, TimetableData>();
let databasePromise: Promise<IDBDatabase | null> | null = null;

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

const transact = async <T>(mode: IDBTransactionMode, operation: (store: IDBObjectStore) => IDBRequest<T>) => {
  const database = await openDatabase();
  if (!database) return undefined;
  return new Promise<T | undefined>((resolve) => {
    const transaction = database.transaction(STORE_NAME, mode);
    const request = operation(transaction.objectStore(STORE_NAME));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(undefined);
    transaction.onerror = () => resolve(undefined);
    transaction.onabort = () => resolve(undefined);
  });
};

const validTimetable = (value: unknown): value is TimetableData =>
  Boolean(value && typeof value === 'object' && Array.isArray((value as TimetableData).items));

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
  const persistedKey = await transact<IDBValidKey>('readwrite', (store) => store.put(data, key));
  if (persistedKey === undefined) {
    try {
      window.localStorage.setItem(`${LEGACY_PREFIX}${key}`, JSON.stringify(data));
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
};

export const deleteTimetableCache = async (email?: string): Promise<void> => {
  const key = normalizeKey(email);
  memoryCache.delete(key);
  await transact('readwrite', (store) => store.delete(key));
  try {
    window.localStorage.removeItem(`${LEGACY_PREFIX}${key}`);
  } catch {
    // Ignore unavailable storage.
  }
};
