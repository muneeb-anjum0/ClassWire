import React from 'react';
import { GroupedTimetable, getCourseCode, getDisplayCampus, getDisplayCourseTitle, getDisplayFaculty, getDisplayRoom, getDisplayTime, renderHighlightedText, shouldHighlightRow } from './timetableTableUtils';

type TimetableMobileSectionProps = {
  grouped: GroupedTimetable;
  sortedSemesters: string[];
};

export default function TimetableMobileSection({
  grouped,
  sortedSemesters,
}: TimetableMobileSectionProps) {
  return (
    <div className="tw-mobile-view">
      {sortedSemesters.map((semester) => (
        <section key={semester} className="tw-mobile-semester">
          <div className="tw-mobile-semester-head">
            <div>
              <p className="tw-section-kicker">Semester</p>
              <h3>{semester}</h3>
            </div>

            <span className="tw-count-pill">{grouped[semester].length} classes</span>
          </div>

          <div className="tw-mobile-card-list">
            {grouped[semester].map((item, itemIndex) => {
              const roomDisplay = getDisplayRoom(item);
              const isOnline = roomDisplay.toLowerCase() === 'online';
              const isCancelled = shouldHighlightRow(item);

              return (
                <article
                  key={`${semester}-${itemIndex}`}
                  className={`tw-class-card ${isCancelled ? 'tw-class-card--cancelled' : ''}`}
                  style={{ animationDelay: `${itemIndex * 45}ms` }}
                >
                  <div className="tw-card-top">
                    <div className="tw-course-block">
                      <span className="tw-course-code" title={getCourseCode(item)}>
                        {renderHighlightedText(getCourseCode(item))}
                      </span>

                      <h4 title={getDisplayCourseTitle(item)}>
                        {renderHighlightedText(getDisplayCourseTitle(item))}
                      </h4>
                    </div>

                    <span className={`tw-room-pill ${isOnline ? 'tw-room-pill--online' : ''}`}>
                      {renderHighlightedText(roomDisplay)}
                    </span>
                  </div>

                  <div className="tw-mobile-details">
                    <div className="tw-detail-row">
                      <span className="tw-detail-label">Time</span>
                      <span className="tw-detail-value">{renderHighlightedText(getDisplayTime(item))}</span>
                    </div>

                    <div className="tw-detail-row">
                      <span className="tw-detail-label">Faculty</span>
                      <span className="tw-detail-value">{renderHighlightedText(getDisplayFaculty(item))}</span>
                    </div>

                    <div className="tw-detail-row tw-detail-row--full">
                      <span className="tw-detail-label">Campus</span>
                      <span className="tw-detail-value">{renderHighlightedText(getDisplayCampus(item))}</span>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
