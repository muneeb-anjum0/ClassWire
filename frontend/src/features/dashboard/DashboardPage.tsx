import React from 'react';
import StatusIndicator from '../../components/StatusIndicator/StatusIndicator';
import TimetableTable from '../../components/TimetableTable/TimetableTable';
import LoginScreen from '../../components/LoginScreen/LoginScreen';
import { useAuth } from '../../context/AuthContext';
import SmartSearch from './SmartSearch';
import { useDashboardController } from './useDashboardController';

export default function DashboardPage() {
  const auth = useAuth();
  const controller = useDashboardController(auth);

  if (!auth.isAuthenticated) {
    return <LoginScreen />;
  }

  return (
    <div className="app-shell">
      <div className="app-shell__content">
        <main className="dashboard-main">
          <SmartSearch
            query={controller.searchQuery}
            setQuery={controller.setSearchQuery}
            onSearch={controller.runSmartSearch}
            onClear={controller.clearSmartSearch}
            loading={controller.isScraperRunning}
            data={controller.timetableData}
            userEmail={controller.userEmail}
            onLogout={controller.handleLogoutClick}
            logoutConfirmArmed={controller.logoutConfirmArmed}
            theme={controller.theme}
            onThemeChange={controller.setTheme}
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

          {controller.timetableData &&
            !controller.isScraperRunning &&
            controller.timetableData.items &&
            controller.timetableData.items.length > 0 && (
              <section
                className={`schedule-panel ${controller.timetableData.search ? 'schedule-panel--search-result' : ''}`}
                aria-labelledby="schedule-heading"
              >
                <div className="schedule-panel__header">
                  <h2 id="schedule-heading">Class schedule</h2>
                  <p className="schedule-panel__meta">
                    <span>{controller.timetableData.for_day || 'Today'}</span>
                    <i aria-hidden="true" />
                    <span>{controller.filteredItems.length} {controller.filteredItems.length === 1 ? 'class' : 'classes'}</span>
                  </p>
                </div>
                <div className="timetable-container">
                  <TimetableTable items={controller.filteredItems} />
                </div>
              </section>
            )}

        </main>

        <footer>
          <div className="app-footer">
            <span>&copy; {new Date().getFullYear()} ClassWire</span>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
          </div>
        </footer>

      </div>
    </div>
  );
}
