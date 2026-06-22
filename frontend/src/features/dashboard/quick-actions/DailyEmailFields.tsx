import React from 'react';
import { Mail, Save, Send } from 'lucide-react';
import { DailyEmailFieldsProps } from './types';

export default function DailyEmailFields({
  compact,
  dailyEmailEnabled,
  isDailyEmailToggleSaving,
  isOperationInProgress,
  isPersonalEmailSaving,
  isTestEmailSending,
  onSavePersonalEmail,
  onSendTestEmail,
  onSetPersonalEmail,
  onToggleDailyEmail,
  personalEmail,
}: DailyEmailFieldsProps) {
  return (
    <>
      <div className="daily-email__label">
        <Mail className="daily-email__icon" aria-hidden="true" />
        <span>Daily email</span>
      </div>

      {!compact && <p>Send the formatted timetable to your personal inbox every day at 8:00 PM.</p>}

      <div className="daily-email__actions">
        <button
          type="button"
          onClick={onToggleDailyEmail}
          disabled={isDailyEmailToggleSaving || isPersonalEmailSaving || isOperationInProgress}
          className="daily-email__toggle"
          aria-pressed={dailyEmailEnabled}
          title={dailyEmailEnabled ? 'Disable daily email delivery' : 'Enable daily email delivery'}
          aria-label={dailyEmailEnabled ? 'Disable daily email delivery' : 'Enable daily email delivery'}
        >
          <span className="daily-email__toggle-track" data-active={dailyEmailEnabled ? 'true' : 'false'}>
            <span className="daily-email__toggle-thumb" />
          </span>
          <span>
            {isDailyEmailToggleSaving
              ? 'Saving'
              : dailyEmailEnabled
                ? compact
                  ? 'On'
                  : 'Enabled'
                : compact
                  ? 'Off'
                  : 'Disabled'}
          </span>
        </button>

        <div className="daily-email__controls">
          <input
            type="email"
            value={personalEmail}
            onChange={(event) => onSetPersonalEmail(event.target.value)}
            placeholder={compact ? 'Personal email' : 'muneeb.anjum0@gmail.com'}
            className="daily-email__input"
            aria-label="Personal email for daily timetable"
          />

          <button
            type="button"
            onClick={onSavePersonalEmail}
            disabled={isPersonalEmailSaving || isTestEmailSending || isOperationInProgress}
            className="daily-email__save"
            title="Save daily email recipient"
            aria-label="Save daily email recipient"
          >
            <Save className="daily-email__save-icon" aria-hidden="true" />
            {!compact && <span>{isPersonalEmailSaving ? 'Saving' : 'Save'}</span>}
          </button>

          <button
            type="button"
            onClick={onSendTestEmail}
            disabled={isPersonalEmailSaving || isTestEmailSending || isOperationInProgress}
            className="daily-email__save daily-email__save--test"
            title="Send mail now"
            aria-label="Send mail now"
          >
            <Send className="daily-email__save-icon" aria-hidden="true" />
            {!compact && <span>{isTestEmailSending ? 'Sending' : 'Send Mail'}</span>}
          </button>
        </div>
      </div>
    </>
  );
}
