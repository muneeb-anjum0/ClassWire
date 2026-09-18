import React from 'react';
import { TimetableData, TimetableItem } from '../../types/api';
import { normalizeSemesterLabel } from '../../utils/semesterNormalization';
import './SummaryStats.css';

interface SummaryStatsProps {
  data: TimetableData;
  filteredItems?: TimetableItem[];
}

const SummaryStats: React.FC<SummaryStatsProps> = ({ data, filteredItems }) => {
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
  const stats = [
    {
      label: 'Total Classes',
      value: displaySummary.total_items || 0,
      icon: '/courses.svg',
      alt: 'Total Classes',
    },
    {
      label: 'Current Day',
      value: data.for_day || 'Today',
      icon: '/day.svg',
      alt: 'Current Day',
    },
  ];

  return (
    <section className="summary-ribbon" aria-label="Timetable summary">
      <div className="summary-ribbon__metrics">
        {stats.map((stat, index) => (
          <div key={stat.label} className={`summary-ribbon__metric summary-ribbon__metric--${index + 1}`}>
            <span className="summary-ribbon__icon">
              <img src={stat.icon} alt="" className="theme-card-icon" />
            </span>
            <span className="summary-ribbon__copy">
              <span className="summary-ribbon__label">{stat.label}</span>
              <strong className="summary-ribbon__value">{stat.value}</strong>
            </span>
          </div>
        ))}
      </div>

    </section>
  );
};

export default SummaryStats;
