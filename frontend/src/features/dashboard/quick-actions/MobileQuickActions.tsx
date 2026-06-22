import React from 'react';
import { ChevronDown } from 'lucide-react';
import ThemeToggle from '../../../components/ThemeToggle/ThemeToggle';
import DailyEmailFields from './DailyEmailFields';
import { QuickActionsPanelProps } from './types';

export default function MobileQuickActions({
  dailyEmailEnabled,
  isDailyEmailToggleSaving,
  isOperationInProgress,
  isPersonalEmailSaving,
  isQuickActionsExpanded,
  isScraperRunning,
  isTestEmailSending,
  lastUpdateDisplay,
  loggedInLabel,
  logoutConfirmArmed,
  noSemestersConfigured,
  onCancelLogoutConfirm,
  onLogout,
  onRunScraper,
  onSavePersonalEmail,
  onSendTestEmail,
  onSetPersonalEmail,
  onShowSemesterManager,
  onThemeToggle,
  onToggleDailyEmail,
  onToggleQuickActions,
  personalEmail,
  quickActionsToggleLabel,
  runButtonText,
  semesterCount,
  theme,
}: QuickActionsPanelProps) {
  return (
    <section className={`quick-mobile ${isQuickActionsExpanded ? 'quick-mobile--expanded' : 'quick-mobile--collapsed'}`}>
      <button
        type="button"
        className="quick-mobile__top"
        onClick={onToggleQuickActions}
        aria-expanded={isQuickActionsExpanded}
        aria-label={quickActionsToggleLabel}
      >
        <span>
          <span className="quick-mobile__eyebrow">Quick Actions</span>
          <span className="quick-mobile__title">Schedule controls</span>
        </span>

        <span className="quick-mobile__chevron" aria-hidden="true">
          <ChevronDown className="quick-mobile__chevron-icon" aria-hidden="true" />
        </span>
      </button>

      <div className="quick-mobile__body">
        <div className="quick-mobile__meta">
          <div className="quick-mobile__meta-card">
            <span className="quick-mobile__meta-label">Logged in</span>
            <span className="quick-mobile__meta-value">{loggedInLabel}</span>
          </div>

          <div className="quick-mobile__meta-card">
            <span className="quick-mobile__meta-label">Last update</span>
            <span className="quick-mobile__meta-value">{lastUpdateDisplay.date}</span>
            <span className="quick-mobile__meta-subvalue">{lastUpdateDisplay.time}</span>
          </div>
        </div>

        <div className="quick-mobile__actions">
          <button
            onClick={onRunScraper}
            disabled={isScraperRunning || isOperationInProgress}
            className={`mobile-action mobile-action--primary ${isScraperRunning ? 'mobile-action--running' : ''}`}
          >
            <span className="mobile-action__text">{runButtonText}</span>
          </button>

          <button
            onClick={onShowSemesterManager}
            className={`mobile-action mobile-action--neutral ${noSemestersConfigured ? 'mobile-action--attention' : ''}`}
          >
            <span className="mobile-action__icon">
              <img src="/setting.svg" alt="" className="theme-button-icon" />
            </span>
            <span className="mobile-action__text">Semesters</span>
            <span className="mobile-action__count">{semesterCount}</span>
          </button>

          <div className="quick-mobile__theme">
            <ThemeToggle theme={theme} onToggle={onThemeToggle} />
            <span>{theme === 'dark' ? 'Dark mode' : 'Light mode'}</span>
          </div>

          <div className="quick-mobile__signout">
            <button
              onClick={onLogout}
              className={`mobile-action mobile-action--logout ${logoutConfirmArmed ? 'mobile-action--danger' : ''}`}
            >
              <span className="mobile-action__icon">
                <img src="/logout.svg" alt="" className="theme-button-icon" />
              </span>
              <span className="mobile-action__text mobile-action__text--wrap">
                {logoutConfirmArmed ? 'Confirm sign out' : 'Sign out'}
              </span>
            </button>

            {logoutConfirmArmed && (
              <button
                onClick={onCancelLogoutConfirm}
                className="mobile-action-cancel"
                title="Cancel sign out"
                aria-label="Cancel sign out"
              >
                ×
              </button>
            )}
          </div>
        </div>

        <div className="daily-email daily-email--mobile">
          <DailyEmailFields
            compact
            dailyEmailEnabled={dailyEmailEnabled}
            isDailyEmailToggleSaving={isDailyEmailToggleSaving}
            isOperationInProgress={isOperationInProgress}
            isPersonalEmailSaving={isPersonalEmailSaving}
            isTestEmailSending={isTestEmailSending}
            onSavePersonalEmail={onSavePersonalEmail}
            onSendTestEmail={onSendTestEmail}
            onSetPersonalEmail={onSetPersonalEmail}
            onToggleDailyEmail={onToggleDailyEmail}
            personalEmail={personalEmail}
          />
        </div>
      </div>
    </section>
  );
}
