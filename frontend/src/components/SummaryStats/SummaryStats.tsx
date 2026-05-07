import React from 'react';
import { TimetableData, ConfigData, TimetableItem } from '../../types/api';
import { normalizeSemesterLabel } from '../../utils/semesterNormalization';

interface SummaryStatsProps {
  data: TimetableData;
  config?: ConfigData;
  filteredItems?: TimetableItem[];
}

const SummaryStats: React.FC<SummaryStatsProps> = ({ data, config, filteredItems }) => {
  if (!data || !data.summary) {
    return null;
  }

  const itemsToAnalyze = filteredItems || data.items || [];

  const calculateFilteredSummary = () => {
    if (itemsToAnalyze.length === 0) {
      return {
        total_items: 0,
        unique_courses: 0,
        unique_faculty: 0,
        semester_breakdown: {},
      };
    }

    const semesterBreakdown: Record<string, number> = {};
    const uniqueCourses = new Set<string>();
    const uniqueFaculty = new Set<string>();

    itemsToAnalyze.forEach((item) => {
      const semKey = normalizeSemesterLabel(
        item.semester_display ||
          item.semester ||
          item.semester_key ||
          item.section ||
          item.class_section
      );

      if (semKey) {
        semesterBreakdown[semKey] = (semesterBreakdown[semKey] || 0) + 1;
      }

      if (item.course_code) {
        uniqueCourses.add(item.course_code);
      }

      if (
        item.faculty &&
        item.faculty.toLowerCase() !== 'cancelled' &&
        item.faculty.toLowerCase() !== 'tbd'
      ) {
        uniqueFaculty.add(item.faculty);
      }
    });

    return {
      total_items: itemsToAnalyze.length,
      unique_courses: uniqueCourses.size,
      unique_faculty: uniqueFaculty.size,
      semester_breakdown: semesterBreakdown,
    };
  };

  const displaySummary = calculateFilteredSummary();
  const semesterCount = Object.keys(displaySummary.semester_breakdown).length;

  const stats = [
    {
      label: 'Total Classes',
      value: displaySummary.total_items || 0,
      icon: '/courses.svg',
      alt: 'Total Classes',
    },
    {
      label: 'Unique Courses',
      value: displaySummary.unique_courses || 0,
      icon: '/uniqueCourses.svg',
      alt: 'Unique Courses',
    },
    {
      label: 'Faculty Members',
      value: displaySummary.unique_faculty || 0,
      icon: '/faculty.svg',
      alt: 'Faculty Members',
    },
    {
      label: 'Current Day',
      value: data.for_day || 'Today',
      icon: '/day.svg',
      alt: 'Current Day',
    },
  ];

  return (
    <>
      <style>
        {`
          @keyframes summaryCardIn {
            from {
              opacity: 0;
              transform: translateY(8px) scale(0.985);
            }

            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }

          .summary-stats-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
          }

          .summary-stat-card {
            position: relative;
            overflow: hidden;
            border-radius: 24px;
            border: 1px solid var(--theme-border-soft, rgba(148, 163, 184, 0.22));
            background:
              linear-gradient(
                135deg,
                color-mix(in srgb, var(--theme-surface, #ffffff) 86%, transparent),
                color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 76%, transparent)
              );
            color: var(--theme-text-primary, #0f172a);
            backdrop-filter: blur(18px) saturate(150%);
            -webkit-backdrop-filter: blur(18px) saturate(150%);
            box-shadow:
              0 12px 30px rgba(15, 23, 42, 0.08),
              inset 0 1px 0 rgba(255, 255, 255, 0.16);
            animation: summaryCardIn 180ms cubic-bezier(.2,.8,.2,1);
            transition:
              transform 160ms ease,
              box-shadow 160ms ease,
              border-color 160ms ease,
              background 160ms ease;
          }

          .summary-stat-card:hover {
            transform: translateY(-2px);
            border-color: var(--theme-border, rgba(148, 163, 184, 0.34));
            background:
              linear-gradient(
                135deg,
                color-mix(in srgb, var(--theme-surface-elevated, #ffffff) 88%, transparent),
                color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 78%, transparent)
              );
            box-shadow:
              0 16px 38px rgba(15, 23, 42, 0.12),
              inset 0 1px 0 rgba(255, 255, 255, 0.18);
          }

          .summary-stat-inner {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px;
          }

          .summary-stat-icon {
            width: 42px;
            height: 42px;
            flex: 0 0 42px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 82%, transparent);
            border: 1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.68));
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14);
          }

          .summary-stat-icon img {
            width: 20px;
            height: 20px;
          }

          .summary-stat-text {
            min-width: 0;
          }

          .summary-stat-label {
            margin: 0;
            color: var(--theme-text-muted, #64748b);
            font-size: 10.5px;
            line-height: 1.1;
            font-weight: 800;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          .summary-stat-value {
            margin: 4px 0 0;
            color: var(--theme-text-primary, #0f172a);
            font-size: 25px;
            line-height: 1;
            font-weight: 850;
            letter-spacing: -0.04em;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          .summary-breakdown-card {
            position: relative;
            overflow: hidden;
            grid-column: span 2;
            border-radius: 26px;
            border: 1px solid var(--theme-border-soft, rgba(148, 163, 184, 0.22));
            background:
              linear-gradient(
                135deg,
                color-mix(in srgb, var(--theme-surface, #ffffff) 88%, transparent),
                color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 78%, transparent)
              );
            backdrop-filter: blur(18px) saturate(150%);
            -webkit-backdrop-filter: blur(18px) saturate(150%);
            box-shadow:
              0 12px 30px rgba(15, 23, 42, 0.08),
              inset 0 1px 0 rgba(255, 255, 255, 0.16);
            animation: summaryCardIn 200ms cubic-bezier(.2,.8,.2,1);
          }

          .summary-breakdown-inner {
            position: relative;
            z-index: 1;
            padding: 16px;
          }

          .summary-breakdown-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 14px;
          }

          .summary-breakdown-title-row {
            display: flex;
            align-items: center;
            gap: 11px;
            min-width: 0;
          }

          .summary-breakdown-icon {
            width: 38px;
            height: 38px;
            flex: 0 0 38px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 82%, transparent);
            border: 1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.68));
            color: var(--theme-text-secondary, #64748b);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
          }

          .summary-breakdown-title {
            margin: 0;
            color: var(--theme-text-primary, #0f172a);
            font-size: 15px;
            font-weight: 850;
            line-height: 1.15;
            letter-spacing: -0.02em;
          }

          .summary-breakdown-subtitle {
            margin: 4px 0 0;
            color: var(--theme-text-secondary, #64748b);
            font-size: 12.5px;
            line-height: 1.35;
          }

          .summary-breakdown-count {
            flex: 0 0 auto;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 28px;
            padding: 0 12px;
            border-radius: 999px;
            border: 1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.68));
            background: color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 78%, transparent);
            color: var(--theme-text-muted, #64748b);
            font-size: 10.5px;
            font-weight: 850;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
          }

          .summary-semester-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
          }

          .summary-semester-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            min-height: 54px;
            padding: 10px 10px 10px 13px;
            border-radius: 999px;
            border: 1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.72));
            background: color-mix(in srgb, var(--theme-surface, #ffffff) 86%, transparent);
            color: var(--theme-text-primary, #0f172a);
            box-shadow: 0 7px 18px rgba(15, 23, 42, 0.055);
            transition:
              transform 150ms ease,
              box-shadow 150ms ease,
              background 150ms ease,
              border-color 150ms ease;
          }

          .summary-semester-card:hover {
            transform: translateY(-1px);
            background: var(--theme-surface-elevated, #ffffff);
            border-color: var(--theme-border, rgba(148, 163, 184, 0.34));
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.085);
          }

          .summary-semester-name {
            margin: 0;
            max-width: 100%;
            color: var(--theme-text-primary, #0f172a);
            font-size: 12.6px;
            font-weight: 800;
            line-height: 1.2;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .summary-semester-caption {
            margin: 2px 0 0;
            color: var(--theme-text-muted, #64748b);
            font-size: 10.5px;
            line-height: 1.2;
          }

          .summary-semester-pill {
            flex: 0 0 auto;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 29px;
            padding: 0 11px;
            border-radius: 999px;
            background: color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 82%, transparent);
            color: var(--theme-text-primary, #0f172a);
            border: 1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.72));
            font-size: 10.5px;
            font-weight: 850;
            white-space: nowrap;
          }

          .summary-empty-state {
            grid-column: span 2;
            border-radius: 22px;
            border: 1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.72));
            background: color-mix(in srgb, var(--theme-surface, #ffffff) 86%, transparent);
            padding: 14px;
            color: var(--theme-text-secondary, #64748b);
            font-size: 12.5px;
            line-height: 1.45;
          }

          @media (min-width: 1024px) {
            .summary-stats-grid {
              grid-template-columns: repeat(4, minmax(0, 1fr));
              gap: 16px;
            }

            .summary-breakdown-card {
              grid-column: span 4;
            }

            .summary-semester-grid {
              grid-template-columns: repeat(3, minmax(0, 1fr));
            }
          }

          @media (max-width: 640px) {
            .summary-stats-grid {
              gap: 10px;
            }

            .summary-stat-card {
              border-radius: 20px;
            }

            .summary-stat-inner {
              padding: 11px;
              gap: 9px;
            }

            .summary-stat-icon {
              width: 35px;
              height: 35px;
              flex-basis: 35px;
            }

            .summary-stat-icon img {
              width: 17px;
              height: 17px;
            }

            .summary-stat-label {
              font-size: 9px;
              letter-spacing: 0.07em;
            }

            .summary-stat-value {
              margin-top: 3px;
              font-size: 20px;
            }

            .summary-breakdown-card {
              border-radius: 22px;
            }

            .summary-breakdown-inner {
              padding: 13px;
            }

            .summary-breakdown-header {
              align-items: flex-start;
              margin-bottom: 12px;
            }

            .summary-breakdown-icon {
              width: 34px;
              height: 34px;
              flex-basis: 34px;
            }

            .summary-breakdown-title {
              font-size: 14px;
            }

            .summary-breakdown-subtitle {
              font-size: 11.5px;
            }

            .summary-breakdown-count {
              min-height: 25px;
              padding: 0 9px;
              font-size: 9px;
              letter-spacing: 0.08em;
            }

            .summary-semester-grid {
              grid-template-columns: 1fr;
              gap: 8px;
            }

            .summary-semester-card {
              min-height: 48px;
              padding: 8px 8px 8px 12px;
            }

            .summary-semester-name {
              font-size: 12.2px;
            }

            .summary-semester-caption {
              font-size: 10px;
            }

            .summary-semester-pill {
              min-height: 26px;
              padding: 0 9px;
              font-size: 10px;
            }

            .summary-empty-state {
              grid-column: span 1;
              border-radius: 18px;
              padding: 12px;
              font-size: 12px;
            }
          }

          @media (max-width: 360px) {
            .summary-stat-inner {
              padding: 10px;
            }

            .summary-stat-icon {
              width: 32px;
              height: 32px;
              flex-basis: 32px;
            }

            .summary-stat-value {
              font-size: 18px;
            }

            .summary-breakdown-count {
              display: none;
            }
          }
        `}
      </style>

      <div className="summary-stats-grid">
        {stats.map((stat) => (
          <div key={stat.label} className="summary-stat-card">
            <div className="summary-stat-inner">
              <div className="summary-stat-icon">
                <img src={stat.icon} alt={stat.alt} className="theme-card-icon" />
              </div>

              <div className="summary-stat-text">
                <p className="summary-stat-label">{stat.label}</p>
                <p className="summary-stat-value">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}

        <div className="summary-breakdown-card">
          <div className="summary-breakdown-inner">
            <div className="summary-breakdown-header">
              <div className="summary-breakdown-title-row">
                <div className="summary-breakdown-icon">
                  <svg
                    width="17"
                    height="17"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                </div>

                <div>
                  <p className="summary-breakdown-title">Semester Breakdown</p>
                  <p className="summary-breakdown-subtitle">
                    Compact class totals by semester.
                  </p>
                </div>
              </div>

              <span className="summary-breakdown-count">
                {semesterCount} semesters
              </span>
            </div>

            <div className="summary-semester-grid">
              {Object.entries(displaySummary.semester_breakdown).length > 0 ? (
                Object.entries(displaySummary.semester_breakdown).map(([semester, count]) => (
                  <div key={semester} className="summary-semester-card">
                    <div style={{ minWidth: 0 }}>
                      <p className="summary-semester-name" title={semester}>
                        {semester}
                      </p>
                      <p className="summary-semester-caption">Scheduled classes</p>
                    </div>

                    <span className="summary-semester-pill">
                      {count} classes
                    </span>
                  </div>
                ))
              ) : (
                <div className="summary-empty-state">
                  No semester data available. Configure your semester filters or refresh the timetable.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default SummaryStats;