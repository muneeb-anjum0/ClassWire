import React, { useEffect, useMemo, useState } from 'react';
import { TimetableItem } from '../../types/api';
import EmptyTimetableState from './EmptyTimetableState';
import TimetableDesktopTable from './TimetableDesktopTable';
import TimetableMobileSection from './TimetableMobileSection';
import './TimetableTable.css';
import { groupAndSortData } from './timetableTableUtils';

interface TimetableTableProps {
  items: TimetableItem[];
}

const EMPTY_ITEMS: TimetableItem[] = [];
const WINDOW_SIZE = 60;

const TimetableTable: React.FC<TimetableTableProps> = ({ items }) => {
  const safeItems = items || EMPTY_ITEMS;
  const [visibleCount, setVisibleCount] = useState(WINDOW_SIZE);
  useEffect(() => setVisibleCount(WINDOW_SIZE), [safeItems]);
  const visibleItems = useMemo(() => safeItems.slice(0, visibleCount), [safeItems, visibleCount]);
  const { grouped, sortedSemesters } = useMemo(
    () => groupAndSortData(visibleItems),
    [visibleItems],
  );
  const showDay = useMemo(
    () => safeItems.some((item) => Boolean(item.schedule_day)),
    [safeItems],
  );

  return (
    <>
      {safeItems.length === 0 ? (
        <EmptyTimetableState />
      ) : (
        <div className="tw-stage">
          <TimetableMobileSection grouped={grouped} sortedSemesters={sortedSemesters} showDay={showDay} />
          <TimetableDesktopTable grouped={grouped} sortedSemesters={sortedSemesters} showDay={showDay} />
          {visibleCount < safeItems.length && <div className="tw-window-controls">
            <span>Showing {visibleItems.length} of {safeItems.length} classes</span>
            <button type="button" onClick={() => setVisibleCount((count) => Math.min(count + WINDOW_SIZE, safeItems.length))}>
              Show {Math.min(WINDOW_SIZE, safeItems.length - visibleCount)} more
            </button>
          </div>}
        </div>
      )}
    </>
  );
};

export default React.memo(TimetableTable);
