import { apiService } from '../../services/api';
import { ConfigData } from '../../types/api';

export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const TEST_EMAIL_POLL_ATTEMPTS = 18;
export const TEST_EMAIL_POLL_INTERVAL_MS = 5000;

export const sleep = (ms: number) =>
  new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });

export async function withInitializeRetry<T>(request: () => Promise<T>, warning: string) {
  try {
    return await request();
  } catch (error) {
    console.warn(warning, error);
    await apiService.initialize();
    return request();
  }
}

export function buildConfigAfterSemesterUpdate(
  currentConfig: ConfigData | null,
  newSemesters: string[],
  personalEmail: string,
): ConfigData {
  return {
    gmail_query: currentConfig?.gmail_query || '',
    semester_filter: newSemesters,
    personal_email: currentConfig?.personal_email || personalEmail.trim(),
    daily_email_enabled: Boolean(currentConfig?.daily_email_enabled),
    schedule_time: currentConfig?.schedule_time || '00:00',
    timezone: currentConfig?.timezone || 'Asia/Karachi',
    max_results: currentConfig?.max_results || 50,
    daily_email_last_result: currentConfig?.daily_email_last_result,
  };
}

export function getCompletedTestEmailMessage(
  lastResult: NonNullable<ConfigData['daily_email_last_result']>,
  fallbackEmail: string,
) {
  const sentSubject = lastResult.send_result?.subject;
  if (sentSubject) {
    return `Accepted by ${lastResult.send_result?.provider || 'provider'}: ${sentSubject}`;
  }

  return lastResult.message || `Mail sent to ${fallbackEmail}.`;
}
