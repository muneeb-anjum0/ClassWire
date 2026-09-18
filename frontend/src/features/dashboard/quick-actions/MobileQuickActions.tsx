import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, Clock3, LogOut, Settings2, UserRound, X } from 'lucide-react';
import ThemeToggle from '../../../components/ThemeToggle/ThemeToggle';
import DailyEmailFields from './DailyEmailFields';
import TimetableDaySelect from './TimetableDaySelect';
import { QuickActionsPanelProps } from './types';

export default function MobileQuickActions(props: QuickActionsPanelProps) {
  const {
    dailyEmailEnabled, isDailyEmailToggleSaving, isOperationInProgress,
    isPersonalEmailSaving, isQuickActionsExpanded, isScraperRunning,
    isTestEmailSending, lastUpdateDisplay, loggedInLabel, logoutConfirmArmed,
    noSemestersConfigured, onCancelLogoutConfirm, onLogout, onRunScraper,
    onSavePersonalEmail, onSendTestEmail, onSetPersonalEmail,
    onShowSemesterManager, onThemeToggle, onToggleDailyEmail, onTimetableDayChange,
    onToggleQuickActions, personalEmail, quickActionsToggleLabel,
    runButtonText, semesterCount, theme, timetableDay,
  } = props;
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
    <section className={`quick-mobile ${isQuickActionsExpanded ? 'quick-mobile--expanded' : 'quick-mobile--collapsed'}`}>
      <div className="quick-mobile__top">
        <button type="button" className="quick-mobile__heading-button" onClick={onToggleQuickActions}>
          <span className="quick-mobile__eyebrow">Quick Actions</span>
          <span className="quick-mobile__title">Schedule controls</span>
        </button>

        <div className="quick-mobile__top-actions">
          <div className="quick-mobile__profile" ref={profileRef}>
            <button type="button" className="quick-mobile__profile-trigger"
              onClick={() => setIsProfileOpen((open) => !open)}
              aria-expanded={isProfileOpen} aria-haspopup="menu"
              aria-label="Open account and email settings">
              <UserRound aria-hidden="true" />
            </button>

            {isProfileOpen && (
              <>
                <button
                  type="button"
                  className="quick-mobile__profile-backdrop"
                  onClick={() => setIsProfileOpen(false)}
                  aria-label="Close account menu"
                />
                <div className="quick-mobile__profile-popover" role="menu">
                <div className="quick-mobile__context">
                  <div className="quick-mobile__context-item">
                    <span className="quick-mobile__context-icon" aria-hidden="true"><UserRound /></span>
                    <span className="quick-mobile__context-copy">
                      <span className="quick-mobile__meta-label">Account</span>
                      <span className="quick-mobile__meta-value">{loggedInLabel}</span>
                    </span>
                  </div>
                  <div className="quick-mobile__context-divider" aria-hidden="true" />
                  <div className="quick-mobile__context-item quick-mobile__context-item--update">
                    <span className="quick-mobile__context-icon" aria-hidden="true"><Clock3 /></span>
                    <span className="quick-mobile__context-copy">
                      <span className="quick-mobile__meta-label">Updated</span>
                      <span className="quick-mobile__meta-value">{lastUpdateDisplay.date}</span>
                      <span className="quick-mobile__meta-subvalue">{lastUpdateDisplay.time}</span>
                    </span>
                  </div>
                </div>

                <div className="daily-email daily-email--mobile">
                  <DailyEmailFields compact dailyEmailEnabled={dailyEmailEnabled}
                    isDailyEmailToggleSaving={isDailyEmailToggleSaving}
                    isOperationInProgress={isOperationInProgress}
                    isPersonalEmailSaving={isPersonalEmailSaving}
                    isTestEmailSending={isTestEmailSending}
                    onSavePersonalEmail={onSavePersonalEmail}
                    onSendTestEmail={onSendTestEmail} onSetPersonalEmail={onSetPersonalEmail}
                    onToggleDailyEmail={onToggleDailyEmail} personalEmail={personalEmail} />
                </div>

                <div className="quick-mobile__profile-footer">
                  <button onClick={onLogout}
                    className={`mobile-action mobile-action--logout ${logoutConfirmArmed ? 'mobile-action--danger' : ''}`}
                    role="menuitem">
                    <span className="mobile-action__icon" aria-hidden="true"><LogOut /></span>
                    <span className="mobile-action__text">{logoutConfirmArmed ? 'Confirm sign out' : 'Sign out'}</span>
                  </button>
                  {logoutConfirmArmed && (
                    <button onClick={onCancelLogoutConfirm} className="mobile-action-cancel" aria-label="Cancel sign out">
                      <X aria-hidden="true" />
                    </button>
                  )}
                </div>
                </div>
              </>
            )}
          </div>

          <button type="button" className="quick-mobile__chevron" onClick={onToggleQuickActions}
            aria-expanded={isQuickActionsExpanded} aria-label={quickActionsToggleLabel}>
            <ChevronDown className="quick-mobile__chevron-icon" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="quick-mobile__body">
        <div className="quick-mobile__actions">
          <button onClick={onRunScraper} disabled={isScraperRunning || isOperationInProgress}
            className={`mobile-action mobile-action--primary ${isScraperRunning ? 'mobile-action--running' : ''}`}>
            <span className="mobile-action__icon mobile-action__icon--primary" aria-hidden="true">↻</span>
            <span className="mobile-action__text">{runButtonText}</span>
          </button>

          <button onClick={onShowSemesterManager}
            className={`mobile-action mobile-action--neutral ${noSemestersConfigured ? 'mobile-action--attention' : ''}`}>
            <span className="mobile-action__icon" aria-hidden="true"><Settings2 /></span>
            <span className="mobile-action__text">Filters</span>
            <span className="mobile-action__count">{semesterCount}</span>
          </button>

          <TimetableDaySelect value={timetableDay} onChange={onTimetableDayChange} />

          <div className="quick-mobile__theme">
            <ThemeToggle theme={theme} onToggle={onThemeToggle} />
            <span>Theme</span>
          </div>
        </div>
      </div>
    </section>
  );
}
