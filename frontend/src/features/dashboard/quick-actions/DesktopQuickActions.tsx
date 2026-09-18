import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, Clock3, LogOut, UserRound, X } from 'lucide-react';
import ThemeToggle from '../../../components/ThemeToggle/ThemeToggle';
import DailyEmailFields from './DailyEmailFields';
import TimetableDaySelect from './TimetableDaySelect';
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
  onTimetableDayChange,
  onThemeToggle,
  onToggleDailyEmail,
  onToggleQuickActions,
  personalEmail,
  quickActionsToggleLabel,
  runButtonText,
  semesterCount,
  theme,
  timetableDay,
  userEmail,
}: QuickActionsPanelProps) {
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isProfileOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (!profileRef.current?.contains(event.target as Node)) setIsProfileOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsProfileOpen(false);
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isProfileOpen]);

  return (
    <section
      className={`surface-card p-4 action-panel ${!isQuickActionsExpanded ? 'action-panel--collapsed' : ''}`}
    >
      <div className="action-panel__header">
        <div className="action-panel__heading">
          <div className="action-panel__heading-copy">
            <p className="action-panel__title">Quick Actions</p>
            <h2>Manage your schedule</h2>
          </div>

          <button
            type="button"
            onClick={onToggleQuickActions}
            className="action-panel__toggle"
            aria-expanded={isQuickActionsExpanded}
            aria-label={quickActionsToggleLabel}
            title={isQuickActionsExpanded ? 'Collapse quick actions' : 'Expand quick actions'}
          >
            <ChevronDown
              className={`action-panel__toggle-icon ${isQuickActionsExpanded ? 'action-panel__toggle-icon--open' : ''}`}
              aria-hidden="true"
            />
          </button>
        </div>

        <div className="action-panel__header-controls">
          <div className="action-panel__meta">
            <div className="action-panel__meta-item">
              <span className="action-panel__meta-icon" aria-hidden="true">
                <Clock3 />
              </span>
              <span className="action-panel__meta-copy">
                <span className="meta-label">Last updated</span>
                <span className="meta-value meta-value--date">
                  <span>{lastUpdateDisplay.date}</span>
                  <span aria-hidden="true">·</span>
                  <span>{lastUpdateDisplay.time}</span>
                </span>
              </span>
            </div>
          </div>

          <div className="profile-menu" ref={profileRef}>
            <button
              type="button"
              className="profile-menu__trigger"
              onClick={() => setIsProfileOpen((open) => !open)}
              aria-expanded={isProfileOpen}
              aria-haspopup="menu"
              aria-label="Open account menu"
            >
              <UserRound aria-hidden="true" />
            </button>

            {isProfileOpen && (
              <div className="profile-menu__popover" role="menu">
                <div className="profile-menu__identity">
                  <span className="profile-menu__avatar" aria-hidden="true">
                    <UserRound />
                  </span>
                  <span className="profile-menu__identity-copy">
                    <span className="profile-menu__label">Signed in as</span>
                    <span className="profile-menu__email">{userEmail}</span>
                  </span>
                </div>

                <div className="profile-menu__actions">
                  <button
                    type="button"
                    onClick={onLogout}
                    className={`profile-menu__logout ${logoutConfirmArmed ? 'profile-menu__logout--armed' : ''}`}
                    role="menuitem"
                  >
                    <LogOut aria-hidden="true" />
                    <span>{logoutConfirmArmed ? 'Confirm sign out' : 'Sign out'}</span>
                  </button>

                  {logoutConfirmArmed && (
                    <button
                      type="button"
                      onClick={onCancelLogoutConfirm}
                      className="profile-menu__cancel"
                      title="Cancel sign out"
                      aria-label="Cancel sign out"
                    >
                      <X aria-hidden="true" />
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className={`action-panel__content ${isQuickActionsExpanded ? 'action-panel__content--open' : 'action-panel__content--collapsed'}`}>
        <div className="action-rail">
          <div className="action-rail__primary">
            <button
              onClick={onRunScraper}
              disabled={isScraperRunning || isOperationInProgress}
              className={`btn-pill btn-pill--primary ${isScraperRunning ? 'btn-pill--running' : ''}`}
            >
              {runButtonText}
            </button>

            <TimetableDaySelect value={timetableDay} onChange={onTimetableDayChange} />

            <ThemeToggle theme={theme} onToggle={onThemeToggle} />

            <button
              onClick={onShowSemesterManager}
              className={`btn-pill btn-pill--neutral ${noSemestersConfigured ? 'btn-pill--attention' : ''}`}
            >
              <img src="/setting.svg" alt="" className="theme-button-icon h-4 w-4 mr-2" />
              Filters
              <span className="count-pill">{semesterCount}</span>
            </button>
          </div>

        </div>

        <div className={`daily-email ${!isQuickActionsExpanded ? 'daily-email--collapsed' : ''}`}>
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
    </section>
  );
}
