import { TimetableItem } from '../../types/api';
import {
  GroupedTimetable,
  ConflictMembership,
  getCourseMeta,
  getConflictPosition,
  getDisplayCampus,
  getDisplayCourseTitle,
  getDisplayFaculty,
  getDisplayRoom,
  getDisplayTime,
  getSemesterLabel,
  getSectionColor,
  groupConflictingItems,
  renderHighlightedText,
  shouldHighlightRow,
  sortTimetableItems,
} from './timetableTableUtils';

type Props = {
  grouped: GroupedTimetable;
  sortedSemesters: string[];
  showDay: boolean;
  conflictMembership: ConflictMembership;
};
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

function ScheduleRow({
  item,
  sectionIndex,
  conflictGroup,
  conflictPosition,
}: {
  item: TimetableItem;
  sectionIndex: number;
  conflictGroup?: string;
  conflictPosition?: string | null;
}) {
  const section = getSemesterLabel(item);
  return <article
    className={`conversation-class ${shouldHighlightRow(item) ? 'conversation-class--cancelled' : ''} ${conflictPosition ? `conversation-class--conflict conversation-class--conflict-${conflictPosition}` : ''}`}
    data-conflict-group={conflictGroup}
    aria-label={conflictPosition ? `${getDisplayCourseTitle(item)}, schedule clash` : undefined}
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
  conflictMembership,
  showHeader = true,
  showCount = true,
}: {
  title: string;
  items: TimetableItem[];
  semesterIndexes: Map<string, number>;
  conflictMembership: ConflictMembership;
  showHeader?: boolean;
  showCount?: boolean;
}) {
  const arrangedItems = groupConflictingItems(items, conflictMembership);
  return <section className="conversation-day">
    {showHeader && <header className="conversation-day__header">
      <h2>{title}</h2>
      {showCount && <span>{items.length} {items.length === 1 ? 'class' : 'classes'}</span>}
    </header>}
    <div className="conversation-day__classes">
      {arrangedItems.map((item, index) => {
        const conflict = conflictMembership.get(item);
        return <ScheduleRow
          key={rowKey(item, index)}
          item={item}
          sectionIndex={semesterIndexes.get(getSemesterLabel(item)) ?? 0}
          conflictGroup={conflict?.groupId}
          conflictPosition={getConflictPosition(arrangedItems, index, conflictMembership)}
        />;
      })}
    </div>
  </section>;
}

export default function TimetableDesktopTable({ grouped, sortedSemesters, showDay, conflictMembership }: Props) {
  const semesterIndexes = new Map(sortedSemesters.map((semester, index) => [semester, index]));
  if (!showDay) {
    return <div className="tw-desktop-view conversation-schedule">
      {sortedSemesters.map((semester) => <ScheduleGroup
        key={semester}
        title={semester}
        items={grouped[semester]}
        semesterIndexes={semesterIndexes}
        conflictMembership={conflictMembership}
        showCount={sortedSemesters.length > 1}
      />)}
    </div>;
  }

  const days = DAY_ORDER.map((day) => ({
    day,
    items: sortTimetableItems(
      sortedSemesters.flatMap((semester) => grouped[semester].filter((item) => item.schedule_day === day)),
    ),
  })).filter(({ items }) => items.length > 0);
  const showDayBreakdown = days.length > 1;

  return <div className="tw-desktop-view conversation-schedule">
    {days.map(({ day, items }) => <ScheduleGroup
      key={day}
      title={day}
      items={items}
      semesterIndexes={semesterIndexes}
      conflictMembership={conflictMembership}
      showHeader={showDayBreakdown}
      showCount={showDayBreakdown}
    />)}
  </div>;
}
