import { fireEvent, render, screen } from '@testing-library/react';
import TimetableTable from '../components/TimetableTable/TimetableTable';

test('large timetables render in bounded windows and can be expanded', () => {
  const items = Array.from({ length: 61 }, (_, index) => ({
    semester_display: 'BS(SE)-7A',
    course_title: `Course ${index + 1}`,
    course_code: `SEC ${1000 + index}`,
    schedule_day: 'Monday',
    time: '08:00 AM - 09:30 AM',
    faculty: 'Teacher',
  }));
  render(<TimetableTable items={items} />);
  expect(screen.getByText('Showing 60 of 61 classes')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Show 1 more' }));
  expect(screen.queryByText('Showing 60 of 61 classes')).not.toBeInTheDocument();
  expect(screen.getAllByText('Course 61').length).toBeGreaterThan(0);
});
