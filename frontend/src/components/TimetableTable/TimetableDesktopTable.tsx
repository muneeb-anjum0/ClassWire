import React from 'react';
import { TimetableItem } from '../../types/api';
import {
  GroupedTimetable,
  getCourseCode,
  getDisplayCampus,
  getDisplayCourseTitle,
  getDisplayFaculty,
  getDisplayRoom,
  getDisplayTime,
  getSemesterLabel,
  renderHighlightedText,
  shouldHighlightRow,
} from './timetableTableUtils';

type Props = { grouped: GroupedTimetable; sortedSemesters: string[]; showDay: boolean };
const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const sectionColor = (index: number): React.CSSProperties => {
  // Golden-angle spacing keeps every semester in the current result visually
  // distinct instead of folding labels into a small repeating palette.
  const hue = Math.round((index * 137.508 + 205) % 360);
  return {
    '--section-bg': `hsl(${hue} 70% 92%)`,
    '--section-border': `hsl(${hue} 58% 67%)`,
    '--section-text': `hsl(${hue} 52% 29%)`,
  } as React.CSSProperties;
};

const rowKey = (item: TimetableItem, index: number) => [
  item.schedule_day,
  getSemesterLabel(item),
  item.course_code || item.course_title || item.course,
  item.faculty,
  item.time,
  item.room,
  item.row_number,
  index,
].join('|');

function ScheduleRow({ item, sectionIndex }: { item: TimetableItem; sectionIndex: number }) {
  const section = getSemesterLabel(item);
  return <article
    className={`conversation-class ${shouldHighlightRow(item) ? 'conversation-class--cancelled' : ''}`}
  >
    <time className="conversation-class__time">{renderHighlightedText(getDisplayTime(item))}</time>
    <div className="conversation-class__course">
      <strong>{renderHighlightedText(getDisplayCourseTitle(item))}</strong>
      <span>{renderHighlightedText(getCourseCode(item))}</span>
    </div>
    <div className="conversation-class__person">
      <small>Faculty</small>
      <span>{renderHighlightedText(getDisplayFaculty(item))}</span>
    </div>
    <div className="conversation-class__place">
      <small>Location</small>
      <span>{renderHighlightedText(getDisplayRoom(item))}</span>
      <em>{renderHighlightedText(getDisplayCampus(item))}</em>
    </div>
    <span className="conversation-class__section" style={sectionColor(sectionIndex)} title={section}>{renderHighlightedText(section)}</span>
  </article>;
}

function ScheduleGroup({ title, items, semesterIndexes }: { title: string; items: TimetableItem[]; semesterIndexes: Map<string, number> }) {
  return <section className="conversation-day">
    <header className="conversation-day__header">
      <h2>{title}</h2>
      <span>{items.length} {items.length === 1 ? 'class' : 'classes'}</span>
    </header>
    <div className="conversation-day__classes">
      {items.map((item, index) => <ScheduleRow key={rowKey(item, index)} item={item} sectionIndex={semesterIndexes.get(getSemesterLabel(item)) ?? 0} />)}
    </div>
  </section>;
}

export default function TimetableDesktopTable({ grouped, sortedSemesters, showDay }: Props) {
  const semesterIndexes = new Map(sortedSemesters.map((semester, index) => [semester, index]));
  if (!showDay) {
    return <div className="tw-desktop-view conversation-schedule">
      {sortedSemesters.map((semester) => <ScheduleGroup key={semester} title={semester} items={grouped[semester]} semesterIndexes={semesterIndexes} />)}
    </div>;
  }

  const days = DAY_ORDER.map((day) => ({
    day,
    items: sortedSemesters.flatMap((semester) => grouped[semester].filter((item) => item.schedule_day === day)),
  })).filter(({ items }) => items.length > 0);

  return <div className="tw-desktop-view conversation-schedule">
    {days.map(({ day, items }) => <ScheduleGroup key={day} title={day} items={items} semesterIndexes={semesterIndexes} />)}
  </div>;
}
