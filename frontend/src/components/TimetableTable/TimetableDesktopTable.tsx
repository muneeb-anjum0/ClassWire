import React from 'react';
import { GroupedTimetable, getCourseCode, getDisplayCampus, getDisplayCourseTitle, getDisplayFaculty, getDisplayRoom, getDisplayTime, getSemesterLabel, renderHighlightedText, shouldHighlightRow } from './timetableTableUtils';
import { TimetableItem } from '../../types/api';

type Props = { grouped: GroupedTimetable; sortedSemesters: string[]; showDay: boolean };
const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

export default function TimetableDesktopTable({ grouped, sortedSemesters, showDay }: Props) {
  const renderItem = (item: TimetableItem, key: string, itemIndex: number) => {
    const roomDisplay = getDisplayRoom(item);
    const isOnline = roomDisplay.toLowerCase() === 'online';
    const isCancelled = shouldHighlightRow(item);
    return (
      <tr key={key} className={`tw-table-row ${isCancelled ? 'tw-table-row--cancelled' : ''}`}
        style={{ animationDelay: `${(itemIndex + 1) * 35}ms` }}>
        <td className="tw-cell--semester"><span className="tw-table-chip tw-table-chip--semester">{renderHighlightedText(getSemesterLabel(item))}</span></td>
        <td className="tw-cell--course"><div className="tw-table-course">
          <span className="tw-table-course-title" title={getDisplayCourseTitle(item)}>{renderHighlightedText(getDisplayCourseTitle(item))}</span>
          <span className="tw-table-course-code">{renderHighlightedText(getCourseCode(item))}</span>
        </div></td>
        <td className="tw-cell--faculty"><span className="tw-muted-text">{renderHighlightedText(getDisplayFaculty(item))}</span></td>
        <td className="tw-cell--room"><span className={`tw-table-chip tw-table-chip--room ${isOnline ? 'tw-table-chip--online' : ''}`}>{renderHighlightedText(roomDisplay)}</span></td>
        <td className="tw-cell--time"><span className="tw-table-chip tw-table-chip--time">{renderHighlightedText(getDisplayTime(item))}</span></td>
        <td className="tw-cell--campus"><span className="tw-campus-chip">{renderHighlightedText(getDisplayCampus(item))}</span></td>
      </tr>
    );
  };

  const dayGroups = DAY_ORDER.map((day) => ({
    day,
    semesters: sortedSemesters.map((semester) => ({ semester, items: grouped[semester].filter((item) => item.schedule_day === day) }))
      .filter((entry) => entry.items.length > 0),
  })).filter((entry) => entry.semesters.length > 0);

  return <div className="tw-desktop-view"><div className="tw-table-shell"><table className="tw-table">
    <thead><tr><th>Semester</th><th>Course Title</th><th>Faculty</th><th>Room</th><th>Time</th><th>Campus</th></tr></thead>
    <tbody>
      {showDay ? dayGroups.map(({ day, semesters }) => (
        <React.Fragment key={day}>
          <tr className={`tw-day-row tw-day-row--${day.toLowerCase()}`}><td colSpan={6}><div className="tw-day-heading"><span>{day}</span><span>{semesters.reduce((sum, entry) => sum + entry.items.length, 0)} classes</span></div></td></tr>
          {semesters.map(({ semester, items }) => (
            <React.Fragment key={`${day}-${semester}`}>
              <tr className="tw-semester-row tw-semester-row--within-day"><td colSpan={6}><div className="tw-semester-title-row"><span className="tw-semester-name">{semester}</span><span className="tw-count-pill">{items.length} classes</span></div></td></tr>
              {items.map((item, index) => renderItem(item, `${day}-${semester}-${index}`, index))}
            </React.Fragment>
          ))}
        </React.Fragment>
      )) : sortedSemesters.map((semester) => (
        <React.Fragment key={semester}>
          <tr className="tw-semester-row"><td colSpan={6}><div className="tw-semester-title-row"><span className="tw-semester-name">{semester}</span><span className="tw-count-pill">{grouped[semester].length} classes</span></div></td></tr>
          {grouped[semester].map((item, index) => renderItem(item, `${semester}-${index}`, index))}
        </React.Fragment>
      ))}
    </tbody>
  </table></div></div>;
}
