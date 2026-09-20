import React from 'react';
import { TimetableItem } from '../../types/api';
import { GroupedTimetable, getCourseMeta, getDisplayCampus, getDisplayCourseTitle, getDisplayFaculty, getDisplayRoom, getDisplayTime, getSectionColor, renderHighlightedText, shouldHighlightRow } from './timetableTableUtils';

type Props = { grouped: GroupedTimetable; sortedSemesters: string[]; showDay: boolean };
const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function ClassCard({ item }: { item: TimetableItem }) {
  const room = getDisplayRoom(item);
  return <article className={`tw-class-card ${shouldHighlightRow(item) ? 'tw-class-card--cancelled' : ''}`}>
    <div className="tw-card-top"><div className="tw-course-block">
      <span className="tw-course-code">{renderHighlightedText(getCourseMeta(item))}</span>
      <h4>{renderHighlightedText(getDisplayCourseTitle(item))}</h4>
    </div><span className={`tw-room-pill ${room.toLowerCase() === 'online' ? 'tw-room-pill--online' : ''}`} title={room}>{renderHighlightedText(room)}</span></div>
    <div className="tw-mobile-details">
      <div className="tw-detail-row tw-detail-row--time"><span className="tw-detail-label">Time</span><span className="tw-detail-value">{renderHighlightedText(getDisplayTime(item))}</span></div>
      <div className="tw-detail-row tw-detail-row--faculty"><span className="tw-detail-label">Faculty</span><span className="tw-detail-value">{renderHighlightedText(getDisplayFaculty(item))}</span></div>
      <div className="tw-detail-row tw-detail-row--campus tw-detail-row--full"><span className="tw-detail-label">Campus</span><span className="tw-detail-value">{renderHighlightedText(getDisplayCampus(item))}</span></div>
    </div>
  </article>;
}

export default function TimetableMobileSection({ grouped, sortedSemesters, showDay }: Props) {
  const semesterIndexes = new Map(sortedSemesters.map((semester, index) => [semester, index]));
  const renderSemester = (semester: string, items: TimetableItem[], key: string, showCount: boolean) => (
    <section key={key} className="tw-mobile-semester">
      <div className="tw-mobile-semester-head">
        <span className="tw-mobile-semester-tag" style={getSectionColor(semesterIndexes.get(semester) ?? 0)} title={semester}>
          <span>{semester}</span>
        </span>
        {showCount && <span className="tw-count-pill">{items.length} {items.length === 1 ? 'class' : 'classes'}</span>}
      </div>
      <div className="tw-mobile-card-list">{items.map((item, index) => <ClassCard key={`${key}-${item.course_code || item.course_title || item.course}-${item.time}-${index}`} item={item} />)}</div>
    </section>
  );

  if (!showDay) return <div className="tw-mobile-view">{sortedSemesters.map((semester) => renderSemester(semester, grouped[semester], semester, sortedSemesters.length > 1))}</div>;

  const days = DAY_ORDER.map((day) => ({
    day,
    semesters: sortedSemesters
      .map((semester) => ({ semester, items: grouped[semester].filter((item) => item.schedule_day === day) }))
      .filter((entry) => entry.items.length),
  })).filter((entry) => entry.semesters.length);
  const showDayHeaders = days.length > 1;

  return <div className="tw-mobile-view tw-mobile-view--weekly">
    {days.map(({ day, semesters }) => {
      return <section key={day} className={`tw-mobile-day tw-mobile-day--${day.toLowerCase()}`}>
        {showDayHeaders && <div className="tw-mobile-day-head"><h2>{day}</h2></div>}
        {semesters.map(({ semester, items }) => renderSemester(semester, items, `${day}-${semester}`, semesters.length > 1))}
      </section>;
    })}
  </div>;
}
