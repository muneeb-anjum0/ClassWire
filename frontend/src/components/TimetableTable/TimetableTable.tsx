import React from 'react';
import { TimetableItem } from '../../types/api';
import EmptyTimetableState from './EmptyTimetableState';
import TimetableDesktopTable from './TimetableDesktopTable';
import TimetableMobileSection from './TimetableMobileSection';
import { groupAndSortData } from './timetableTableUtils';
import { timetableStyles } from './timetableStyles';

interface TimetableTableProps {
  items: TimetableItem[];
}

const TimetableTable: React.FC<TimetableTableProps> = ({ items }) => {
  const safeItems = items || [];
  const { grouped, sortedSemesters } = groupAndSortData(safeItems);
  const showDay = safeItems.some((item) => Boolean(item.schedule_day));

  return (
    <>
      <style>{timetableStyles}</style>

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

export default TimetableTable;
