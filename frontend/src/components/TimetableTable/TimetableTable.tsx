import React, { useMemo } from 'react';
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

const TimetableTable: React.FC<TimetableTableProps> = ({ items }) => {
  const safeItems = items || EMPTY_ITEMS;
  const { grouped, sortedSemesters } = useMemo(
    () => groupAndSortData(safeItems),
    [safeItems],
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
        </div>
      )}
    </>
  );
};

export default React.memo(TimetableTable);
