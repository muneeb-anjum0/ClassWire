import React, { FormEvent, useState } from 'react';
import { ArrowRight, LogOut, Search, UserRound } from 'lucide-react';
import { TimetableData } from '../../types/api';
import './smart-search.css';

type Props = {
  query: string;
  setQuery: (value: string) => void;
  onSearch: (query?: string) => void;
  loading: boolean;
  data: TimetableData | null;
  userEmail?: string;
  onLogout: () => void;
};

const EXAMPLES = [
  'Timetable for BSSE 7A for the entire week',
  'When does Zainab have classes?',
  'When is Zainab free on Monday?',
  'Show every Software course on Friday',
];

export default function SmartSearch({ query, setQuery, onSearch, loading, data, userEmail, onLogout }: Props) {
  const [accountOpen, setAccountOpen] = useState(false);
  const submit = (event: FormEvent) => { event.preventDefault(); onSearch(); };
  const result = data?.search;
  const availability = result?.faculty_availability || [];
  const readableTime = (slot: string) => slot.replace(' – ', ' to ');
  return <section className="smart-search">
    <div className="smart-search__account">
      <button onClick={() => setAccountOpen(!accountOpen)} aria-label="Account"><UserRound /></button>
      {accountOpen && <div><p>{userEmail}</p><button onClick={onLogout}><LogOut /> Sign out</button></div>}
    </div>
    <form onSubmit={submit} className="smart-search__form">
      <Search aria-hidden="true" />
      <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask: When is Zainab free on Monday?" aria-label="Search timetable" />
      <button type="submit" disabled={loading || query.trim().length < 2} aria-label="Search timetable">{loading ? <span className="smart-search__loader" /> : <><span>Search</span><ArrowRight /></>}</button>
    </form>
    <div className="smart-search__examples">{EXAMPLES.map((example) => <button key={example} onClick={() => { setQuery(example); onSearch(example); }}>{example}</button>)}</div>
    {result && <div className="smart-search__answer">
      {availability.length > 0 ? <div className="smart-search__availability">
        {availability.map(({ faculty, slots }) => Object.entries(slots).map(([day, freeSlots]) => <div className="smart-search__person" key={`${faculty}-${day}`}>
          <p><strong>{faculty}</strong> is free on <strong>{day}</strong> during university hours in the following slots:</p>
          {freeSlots.length > 0
            ? <ol>{freeSlots.map((slot) => <li key={slot}>{readableTime(slot)}</li>)}</ol>
            : <p className="smart-search__none">No free time between 8:00 AM and 9:30 PM.</p>}
        </div>))}
      </div> : <p>{result.answer}</p>}
    </div>}
  </section>;
}
