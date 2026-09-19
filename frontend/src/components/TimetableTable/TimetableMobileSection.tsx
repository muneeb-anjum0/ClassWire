import React from 'react';
import { TimetableItem } from '../../types/api';
import { GroupedTimetable, getCourseCode, getDisplayCampus, getDisplayCourseTitle, getDisplayFaculty, getDisplayRoom, getDisplayTime, renderHighlightedText, shouldHighlightRow } from './timetableTableUtils';

type Props = { grouped: GroupedTimetable; sortedSemesters: string[]; showDay: boolean };
const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function ClassCard({ item }: { item: TimetableItem }) {
  const room = getDisplayRoom(item);
  return <article className={`tw-class-card ${shouldHighlightRow(item) ? 'tw-class-card--cancelled' : ''}`}>
    <div className="tw-card-top"><div className="tw-course-block">
      <span className="tw-course-code">{renderHighlightedText(getCourseCode(item))}</span>
      <h4>{renderHighlightedText(getDisplayCourseTitle(item))}</h4>
    </div><span className={`tw-room-pill ${room.toLowerCase() === 'online' ? 'tw-room-pill--online' : ''}`}>{renderHighlightedText(room)}</span></div>
    <div className="tw-mobile-details">
      <div className="tw-detail-row tw-detail-row--time"><span className="tw-detail-label">Time</span><span className="tw-detail-value">{renderHighlightedText(getDisplayTime(item))}</span></div>
      <div className="tw-detail-row tw-detail-row--faculty"><span className="tw-detail-label">Faculty</span><span className="tw-detail-value">{renderHighlightedText(getDisplayFaculty(item))}</span></div>
      <div className="tw-detail-row tw-detail-row--campus tw-detail-row--full"><span className="tw-detail-label">Campus</span><span className="tw-detail-value">{renderHighlightedText(getDisplayCampus(item))}</span></div>
    </div>
  </article>;
}

export default function TimetableMobileSection({ grouped, sortedSemesters, showDay }: Props) {
  const renderSemester = (semester: string, items: TimetableItem[], key: string) => (
    <section key={key} className="tw-mobile-semester">
      <div className="tw-mobile-semester-head"><div><p className="tw-section-kicker">Semester</p><h3>{semester}</h3></div><span className="tw-count-pill">{items.length} classes</span></div>
      <div className="tw-mobile-card-list">{items.map((item, index) => <ClassCard key={`${key}-${item.course_code || item.course_title || item.course}-${item.time}-${index}`} item={item} />)}</div>
    </section>
  );

  if (!showDay) return <div className="tw-mobile-view">{sortedSemesters.map((semester) => renderSemester(semester, grouped[semester], semester))}</div>;

  return <div className="tw-mobile-view tw-mobile-view--weekly">
    {DAY_ORDER.map((day) => {
      const semesters = sortedSemesters.map((semester) => ({ semester, items: grouped[semester].filter((item) => item.schedule_day === day) })).filter((entry) => entry.items.length);
      if (!semesters.length) return null;
      const count = semesters.reduce((sum, entry) => sum + entry.items.length, 0);
      return <section key={day} className={`tw-mobile-day tw-mobile-day--${day.toLowerCase()}`}>
        <div className="tw-mobile-day-head"><div><p className="tw-section-kicker">Schedule</p><h2>{day}</h2></div><span className="tw-count-pill">{count} classes</span></div>
        {semesters.map(({ semester, items }) => renderSemester(semester, items, `${day}-${semester}`))}
      </section>;
    })}
  </div>;
}
