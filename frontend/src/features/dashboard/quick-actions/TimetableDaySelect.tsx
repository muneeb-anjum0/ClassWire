import React from 'react';
import { CalendarDays } from 'lucide-react';

const DAYS = ['Auto', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Entire Week'];

export default function TimetableDaySelect({ value, onChange }: { value: string; onChange: (day: string) => void }) {
  return (
    <label className="timetable-day-select">
      <CalendarDays aria-hidden="true" />
      <span className="timetable-day-select__label">Show</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} aria-label="Timetable day to search">
        {DAYS.map((day) => <option key={day} value={day}>{day}</option>)}
      </select>
    </label>
  );
}
