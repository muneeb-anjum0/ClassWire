import React from 'react';
import { TimetableItem } from '../../types/api';
import {
  GroupedTimetable,
  getCourseMeta,
  getDisplayCampus,
  getDisplayCourseTitle,
  getDisplayFaculty,
  getDisplayRoom,
  getDisplayTime,
  getSemesterLabel,
  getSectionColor,
  renderHighlightedText,
  shouldHighlightRow,
} from './timetableTableUtils';

type Props = { grouped: GroupedTimetable; sortedSemesters: string[]; showDay: boolean };
const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
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
      <span>{renderHighlightedText(getCourseMeta(item))}</span>
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
    <span className="conversation-class__section" style={getSectionColor(sectionIndex)} title={section}>
      <span>{renderHighlightedText(section)}</span>
    </span>
  </article>;
}

function ScheduleGroup({
  title,
  items,
  semesterIndexes,
  showHeader = true,
  showCount = true,
}: {
  title: string;
  items: TimetableItem[];
  semesterIndexes: Map<string, number>;
  showHeader?: boolean;
  showCount?: boolean;
}) {
  return <section className="conversation-day">
    {showHeader && <header className="conversation-day__header">
      <h2>{title}</h2>
      {showCount && <span>{items.length} {items.length === 1 ? 'class' : 'classes'}</span>}
    </header>}
    <div className="conversation-day__classes">
      {items.map((item, index) => <ScheduleRow key={rowKey(item, index)} item={item} sectionIndex={semesterIndexes.get(getSemesterLabel(item)) ?? 0} />)}
    </div>
  </section>;
}

export default function TimetableDesktopTable({ grouped, sortedSemesters, showDay }: Props) {
  const semesterIndexes = new Map(sortedSemesters.map((semester, index) => [semester, index]));
  if (!showDay) {
    return <div className="tw-desktop-view conversation-schedule">
      {sortedSemesters.map((semester) => <ScheduleGroup
        key={semester}
        title={semester}
        items={grouped[semester]}
        semesterIndexes={semesterIndexes}
        showCount={sortedSemesters.length > 1}
      />)}
    </div>;
  }

  const days = DAY_ORDER.map((day) => ({
    day,
    items: sortedSemesters.flatMap((semester) => grouped[semester].filter((item) => item.schedule_day === day)),
  })).filter(({ items }) => items.length > 0);
  const showDayBreakdown = days.length > 1;

  return <div className="tw-desktop-view conversation-schedule">
    {days.map(({ day, items }) => <ScheduleGroup
      key={day}
      title={day}
      items={items}
      semesterIndexes={semesterIndexes}
      showHeader={showDayBreakdown}
      showCount={showDayBreakdown}
    />)}
  </div>;
}
