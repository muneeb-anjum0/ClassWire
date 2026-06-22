import React from 'react';
import { ChevronDown } from 'lucide-react';
import ThemeToggle from '../../../components/ThemeToggle/ThemeToggle';
import DailyEmailFields from './DailyEmailFields';
import { QuickActionsPanelProps } from './types';

export default function DesktopQuickActions({
  dailyEmailEnabled,
  isDailyEmailToggleSaving,
  isOperationInProgress,
  isPersonalEmailSaving,
  isQuickActionsExpanded,
  isScraperRunning,
  isTestEmailSending,
  lastUpdateDisplay,
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
  userEmail,
}: QuickActionsPanelProps) {
  return (
    <section
      className={`surface-card p-4 action-panel ${!isQuickActionsExpanded ? 'action-panel--collapsed' : ''}`}
    >
      <div className="action-panel__header">
        <div className="action-panel__heading">
          <p className="action-panel__title">Quick Actions</p>
          <h2>Manage your schedule</h2>
        </div>

        <div className="action-panel__header-controls">
          <div className="action-panel__meta">
            <div className="action-panel__meta-item">
              <span className="meta-label">Logged in</span>
              <span className="meta-value theme-text-primary">{userEmail}</span>
            </div>

            <div className="action-panel__meta-item">
              <span className="meta-label">Last updated</span>
              <span className="meta-value meta-value--stacked">
                <span>{lastUpdateDisplay.date}</span>
                <span>{lastUpdateDisplay.time}</span>
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onToggleQuickActions}
            className="action-panel__toggle"
            aria-expanded={isQuickActionsExpanded}
            aria-label={quickActionsToggleLabel}
          >
            <span>{isQuickActionsExpanded ? 'Collapse' : 'Expand'}</span>
            <ChevronDown
              className={`action-panel__toggle-icon ${isQuickActionsExpanded ? 'action-panel__toggle-icon--open' : ''}`}
              aria-hidden="true"
            />
          </button>
        </div>
      </div>

      <div className="action-panel__content action-panel__content--open">
        <div className="action-rail">
          <button
            onClick={onRunScraper}
            disabled={isScraperRunning || isOperationInProgress}
            className={`btn-pill btn-pill--primary ${isScraperRunning ? 'btn-pill--running' : ''}`}
          >
            {runButtonText}
          </button>

          <ThemeToggle theme={theme} onToggle={onThemeToggle} />

          <button
            onClick={onShowSemesterManager}
            className={`btn-pill btn-pill--neutral ${noSemestersConfigured ? 'btn-pill--attention' : ''}`}
          >
            <img src="/setting.svg" alt="Settings" className="theme-button-icon h-4 w-4 mr-2" />
            Semesters
            <span className="count-pill">{semesterCount}</span>
          </button>

          <div className="inline-flex items-center">
            <button
              onClick={onLogout}
              className={`signout-chip ${logoutConfirmArmed ? 'signout-chip--armed' : 'signout-chip--idle'}`}
            >
              <img src="/logout.svg" alt="Logout" className="theme-button-icon signout-chip__icon" />
              <span className="signout-chip__text">{logoutConfirmArmed ? 'Confirm' : 'Sign Out'}</span>
            </button>

            {logoutConfirmArmed && (
              <button
                onClick={onCancelLogoutConfirm}
                className="signout-cancel"
                title="Cancel sign out"
                aria-label="Cancel sign out"
              >
                <span className="signout-cancel__mark" aria-hidden="true">×</span>
                <span className="signout-cancel__text">Cancel</span>
              </button>
            )}
          </div>
        </div>

        <div className={`daily-email ${!isQuickActionsExpanded ? 'daily-email--collapsed' : ''}`}>
          <div className="daily-email__copy">
            <DailyEmailFields
              compact={false}
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
      </div>
    </section>
  );
}
