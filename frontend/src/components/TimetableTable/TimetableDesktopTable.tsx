import React from 'react';
import { GroupedTimetable, getCourseCode, getDisplayCampus, getDisplayCourseTitle, getDisplayFaculty, getDisplayRoom, getDisplayTime, getSemesterLabel, renderHighlightedText, shouldHighlightRow } from './timetableTableUtils';

type TimetableDesktopTableProps = {
  grouped: GroupedTimetable;
  sortedSemesters: string[];
};

export default function TimetableDesktopTable({
  grouped,
  sortedSemesters,
}: TimetableDesktopTableProps) {
  return (
    <div className="tw-desktop-view">
      <div className="tw-table-shell">
        <table className="tw-table">
          <thead>
            <tr>
              <th>Semester</th>
              <th>Course Title</th>
              <th>Faculty</th>
              <th>Room</th>
              <th>Time</th>
              <th>Campus</th>
            </tr>
          </thead>

          <tbody>
            {sortedSemesters.map((semester) => (
              <React.Fragment key={semester}>
                <tr className="tw-semester-row">
                  <td colSpan={6}>
                    <div className="tw-semester-title-row">
                      <span className="tw-semester-name">{semester}</span>
                      <span className="tw-count-pill">{grouped[semester].length} classes</span>
                    </div>
                  </td>
                </tr>

                {grouped[semester].map((item, itemIndex) => {
                  const roomDisplay = getDisplayRoom(item);
                  const isOnline = roomDisplay.toLowerCase() === 'online';
                  const isCancelled = shouldHighlightRow(item);

                  return (
                    <tr
                      key={`${semester}-${itemIndex}`}
                      className={`tw-table-row ${isCancelled ? 'tw-table-row--cancelled' : ''}`}
                      style={{ animationDelay: `${(itemIndex + 1) * 35}ms` }}
                    >
                      <td>
                        <span className="tw-table-chip">{renderHighlightedText(getSemesterLabel(item))}</span>
                      </td>

                      <td>
                        <div className="tw-table-course">
                          <span className="tw-table-course-title" title={getDisplayCourseTitle(item)}>
                            {renderHighlightedText(getDisplayCourseTitle(item))}
                          </span>
                          <span className="tw-table-course-code">
                            {renderHighlightedText(getCourseCode(item))}
                          </span>
                        </div>
                      </td>

                      <td>
                        <span className="tw-muted-text">{renderHighlightedText(getDisplayFaculty(item))}</span>
                      </td>

                      <td>
                        <span className={`tw-table-chip ${isOnline ? 'tw-table-chip--online' : ''}`}>
                          {renderHighlightedText(roomDisplay)}
                        </span>
                      </td>

                      <td>
                        <span className="tw-table-chip tw-table-chip--time">
                          {renderHighlightedText(getDisplayTime(item))}
                        </span>
                      </td>

                      <td>
                        <span className="tw-campus-chip">{renderHighlightedText(getDisplayCampus(item))}</span>
                      </td>
                    </tr>
                  );
                })}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
