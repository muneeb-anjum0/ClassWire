import { Dispatch, SetStateAction, useEffect, useState } from 'react';
import { apiService } from '../../services/api';
import { ConfigData } from '../../types/api';
import {
  EMAIL_PATTERN,
  getCompletedTestEmailMessage,
  sleep,
  TEST_EMAIL_POLL_ATTEMPTS,
  TEST_EMAIL_POLL_INTERVAL_MS,
} from './dashboardApi';
import { DashboardStatus } from './dashboardControllerTypes';

type ShowStatus = (status: DashboardStatus, message: string) => void;

interface EmailActionsOptions {
  checkStatus: () => Promise<void>;
  config: ConfigData | null;
  loadConfig: () => Promise<ConfigData | null>;
  operationInProgress: boolean;
  setConfig: Dispatch<SetStateAction<ConfigData | null>>;
  showStatus: ShowStatus;
}

export function useDashboardEmailActions({
  checkStatus,
  config,
  loadConfig,
  operationInProgress,
  setConfig,
  showStatus,
}: EmailActionsOptions) {
  const [personalEmail, setPersonalEmail] = useState('');
  const [isPersonalEmailSaving, setIsPersonalEmailSaving] = useState(false);
  const [isDailyEmailToggleSaving, setIsDailyEmailToggleSaving] = useState(false);
  const [isTestEmailSending, setIsTestEmailSending] = useState(false);
  const dailyEmailEnabled = Boolean(config?.daily_email_enabled);

  useEffect(() => {
    setPersonalEmail(config?.personal_email || '');
  }, [config?.personal_email]);

  const savePersonalEmail = async () => {
    if (isPersonalEmailSaving || operationInProgress) return;

    const email = personalEmail.trim();
    if (email && !EMAIL_PATTERN.test(email)) {
      showStatus('error', 'Please enter a valid personal email address.');
      return;
    }

    try {
      setIsPersonalEmailSaving(true);
      showStatus('loading', email ? 'Saving daily email recipient...' : 'Disabling daily email delivery...');
      const response = await apiService.updatePersonalEmail(email);
      if (!response.success) {
        showStatus('error', response.error || 'Failed to save daily email recipient');
        return;
      }

      const enabled = response.data?.daily_email_enabled ?? false;
      setPersonalEmail(email);
      setConfig((current) => current && {
        ...current,
        personal_email: email,
        daily_email_enabled: enabled,
      });
      showStatus(
        'success',
        !email
          ? 'Daily timetable email disabled.'
          : enabled
            ? 'Daily timetable email saved. Automation will send it at 8:00 PM.'
            : 'Recipient saved. Turn on daily email when you want automatic delivery.',
      );
    } catch (error) {
      console.error('Error saving personal email:', error);
      showStatus('error', 'Failed to save daily email recipient');
    } finally {
      setIsPersonalEmailSaving(false);
    }
  };

  const toggleDailyEmail = async () => {
    if (isDailyEmailToggleSaving || operationInProgress) return;

    const nextEnabled = !dailyEmailEnabled;
    if (nextEnabled && !config?.personal_email?.trim()) {
      showStatus('error', 'Save a personal email before enabling daily delivery.');
      return;
    }

    try {
      setIsDailyEmailToggleSaving(true);
      showStatus('loading', nextEnabled ? 'Enabling daily email delivery...' : 'Disabling daily email delivery...');
      const response = await apiService.updateDailyEmailEnabled(nextEnabled);
      if (!response.success) {
        showStatus('error', response.error || 'Failed to update daily email delivery');
        return;
      }

      const enabled = response.data?.daily_email_enabled ?? nextEnabled;
      setConfig((current) => current && {
        ...current,
        daily_email_enabled: enabled,
        personal_email: response.data?.personal_email ?? current.personal_email,
      });
      showStatus('success', enabled ? 'Daily email enabled. It will run at 8:00 PM.' : 'Daily email disabled.');
    } catch (error) {
      console.error('Error toggling daily email:', error);
      showStatus('error', 'Failed to update daily email delivery');
    } finally {
      setIsDailyEmailToggleSaving(false);
    }
  };

  const sendTestEmail = async () => {
    if (isTestEmailSending || operationInProgress) return;

    const email = personalEmail.trim();
    if (!email) {
      showStatus('error', 'Save a personal email before sending a test.');
      return;
    }
    if (email !== config?.personal_email?.trim()) {
      showStatus('warning', 'Save the personal email first, then send mail.');
      return;
    }

    try {
      setIsTestEmailSending(true);
      showStatus('loading', 'Running parser and sending mail...');
      const response = await apiService.sendTestTimetableEmail();
      if (!response.success) {
        showStatus('error', response.error || 'Failed to send mail');
        return;
      }

      showStatus('success', `Mail send started for ${email}. Check your inbox in a minute.`);
      for (let attempt = 0; attempt < TEST_EMAIL_POLL_ATTEMPTS; attempt += 1) {
        await sleep(TEST_EMAIL_POLL_INTERVAL_MS);
        const result = (await loadConfig())?.daily_email_last_result;
        if (result?.status === 'scraping' || result?.status === 'sending') {
          showStatus('loading', result.message || 'Mail send is still running...');
          continue;
        }
        if (result?.status === 'success') {
          showStatus('success', getCompletedTestEmailMessage(result, email));
          await checkStatus();
          return;
        }
        if (result?.status === 'error') {
          showStatus('error', result.error || result.message || 'Mail send failed. Check SMTP settings.');
          return;
        }
      }
      showStatus('warning', 'Mail send is still running. Check the backend logs for the background job.');
    } catch (error) {
      console.error('Error sending mail:', error);
      showStatus('error', 'Failed to send mail');
    } finally {
      setIsTestEmailSending(false);
    }
  };

  return {
    dailyEmailEnabled,
    handleSavePersonalEmail: savePersonalEmail,
    handleSendTestEmail: sendTestEmail,
    handleToggleDailyEmail: toggleDailyEmail,
    isDailyEmailToggleSaving,
    isPersonalEmailSaving,
    isTestEmailSending,
    personalEmail,
    setPersonalEmail,
  };
}
