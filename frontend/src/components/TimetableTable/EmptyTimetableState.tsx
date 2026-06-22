import React from 'react';

export default function EmptyTimetableState() {
  return (
    <div className="tw-empty-state">
      <div className="tw-empty-icon" aria-hidden="true">
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.6}
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </div>

      <h3>No timetable data available</h3>
      <p>Configure your semesters and refresh the data to see your schedule.</p>
    </div>
  );
}
