import React from 'react';
import { TimetableData, ConfigData, TimetableItem } from '../../types/api';
import { normalizeSemesterLabel } from '../../utils/semesterNormalization';
import './SummaryStats.css';

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
