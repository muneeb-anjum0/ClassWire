import React from 'react';
import StatusIndicator from '../../components/StatusIndicator/StatusIndicator';
import SummaryStats from '../../components/SummaryStats/SummaryStats';
import TimetableTable from '../../components/TimetableTable/TimetableTable';
import SemesterManager from '../../components/SemesterManager/SemesterManager';
import LoginScreen from '../../components/LoginScreen/LoginScreen';
import { useAuth } from '../../context/AuthContext';
import QuickActionsPanel from './QuickActionsPanel';
import { useDashboardController } from './useDashboardController';

export default function DashboardPage() {
  const auth = useAuth();
  const controller = useDashboardController(auth);

  if (controller.authLoading) {
    return (
      <div className="app-loading-screen">
        <div className="app-loading-card">
          <div className="app-loading-spinner" />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return <LoginScreen />;
  }

  return (
    <div className="app-shell min-h-screen">
      <div className="app-shell__overlay" />

      <div className="relative z-10">
        <header className="topbar sticky top-0 z-40">
          <div className="layout-shell px-4 sm:px-6 lg:px-8 py-2" />
        </header>

        <main className="layout-shell px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-5 sm:space-y-6">
          <QuickActionsPanel
            dailyEmailEnabled={controller.dailyEmailEnabled}
            isDailyEmailToggleSaving={controller.isDailyEmailToggleSaving}
            isMobile={controller.isMobileQuickActions}
            isOperationInProgress={controller.operationInProgress}
            isPersonalEmailSaving={controller.isPersonalEmailSaving}
            isQuickActionsExpanded={controller.isQuickActionsExpanded}
            isScraperRunning={controller.isScraperRunning}
            isSemesterUpdateRunning={controller.isSemesterUpdateRunning}
            isTestEmailSending={controller.isTestEmailSending}
            lastUpdateDisplay={controller.lastUpdateDisplay}
            loggedInLabel={controller.loggedInLabel}
            logoutConfirmArmed={controller.logoutConfirmArmed}
            noSemestersConfigured={controller.noSemestersConfigured}
            onCancelLogoutConfirm={controller.cancelLogoutConfirm}
            onLogout={controller.handleLogoutClick}
            onRunScraper={controller.runScraper}
            onSavePersonalEmail={controller.handleSavePersonalEmail}
            onSendTestEmail={controller.handleSendTestEmail}
            onSetPersonalEmail={controller.setPersonalEmail}
            onShowSemesterManager={() => controller.setShowSemesterManager(true)}
            onThemeToggle={() => controller.setTheme(controller.theme === 'dark' ? 'light' : 'dark')}
            onToggleDailyEmail={controller.handleToggleDailyEmail}
            onToggleQuickActions={() =>
              controller.setIsQuickActionsExpanded((current) => !current)
            }
            personalEmail={controller.personalEmail}
            quickActionsToggleLabel={controller.quickActionsToggleLabel}
            runButtonText={controller.runButtonText}
            semesterCount={controller.semesterCount}
            theme={controller.theme}
            userEmail={controller.userEmail}
          />

          {(controller.status !== 'idle' || controller.isBackendWaking || controller.isStatusToastClosing) && (
            <StatusIndicator
              status={
                controller.status === 'loading'
                  ? 'loading'
                  : controller.status === 'success'
                  ? 'success'
                  : controller.status === 'warning'
                  ? 'warning'
                  : controller.status === 'error'
                  ? 'error'
                  : 'success'
              }
              message={
                controller.isBackendWaking
                  ? controller.message || 'Backend is waking up on Render. First request after inactivity can take about a minute.'
                  : controller.message ||
                    (controller.detectedSemesters.length > 0
                      ? `${controller.detectedSemesters.length} semester(s) configured`
                      : 'Ready to configure semesters')
              }
              closing={controller.isStatusToastClosing}
              onDismiss={controller.dismissStatus}
            />
          )}

          {controller.timetableData && !controller.isScraperRunning && (
            <section className="animate-timetable-enter">
              <SummaryStats
                data={controller.timetableData}
                config={controller.config || undefined}
                filteredItems={controller.filteredItems}
              />
            </section>
          )}

          {controller.timetableData &&
            !controller.isScraperRunning &&
            controller.timetableData.items &&
            controller.timetableData.items.length > 0 && (
              <section className="surface-card overflow-hidden animate-timetable-enter">
                <div className="surface-card__header">
                  <h3 className="text-lg font-semibold theme-text-primary tracking-tight">Class Schedule</h3>
                  <div className="flex items-center gap-2 timetable-count-pill rounded-full px-3 py-1 border">
                    <img src="/pulse.svg" alt="Pulse" className="theme-button-icon h-4 w-4" />
                    <span className="text-sm font-medium">{controller.filteredItems.length} classes</span>
                  </div>
                </div>
                <div className="p-0 timetable-container">
                  <TimetableTable items={controller.filteredItems} />
                </div>
              </section>
            )}

          {controller.noSemestersConfigured && !controller.isScraperRunning && (
            <section className="surface-card surface-card--compact surface-card--callout animate-timetable-enter">
              <div className="compact-callout compact-callout--stacked">
                <div className="compact-callout__content">
                  <p className="compact-callout__eyebrow">Schedule setup</p>
                  <h3 className="compact-callout__title">Ready when you are</h3>
                  <p className="compact-callout__text">
                    Configure your semesters in Semester Manager, then run the scraper from Quick Actions to populate and organize your timetable.
                  </p>
                </div>
              </div>
            </section>
          )}
        </main>

        <footer className="bg-transparent border-0">
          <div className="app-footer">
            <span>&copy; {new Date().getFullYear()} ClassWire</span>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
          </div>
        </footer>

        <SemesterManager
          isOpen={controller.showSemesterManager}
          onClose={() => controller.setShowSemesterManager(false)}
          currentSemesters={controller.detectedSemesters}
          onSave={controller.handleSaveSemesters}
        />
      </div>
    </div>
  );
}
