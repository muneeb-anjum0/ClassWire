import { deleteTimetableCache } from './timetableCache';

const USER_STORAGE_PREFIXES = [
  'classwire:v2:last-search:',
  'classwire:v3:recent-searches:',
  'classwire:v3:suggestion-history:',
];

export const deleteLocalAccountData = async (email?: string): Promise<void> => {
  const normalizedEmail = (email || '').trim().toLowerCase();
  await deleteTimetableCache(normalizedEmail || undefined);

  if (!normalizedEmail) return;

  try {
    USER_STORAGE_PREFIXES.forEach((prefix) => {
      window.localStorage.removeItem(`${prefix}${normalizedEmail}`);
    });
  } catch {
    // Server-side deletion remains authoritative when browser storage is
    // unavailable or blocked by privacy settings.
  }
};
