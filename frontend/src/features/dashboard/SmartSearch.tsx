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
const WEEKDAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

export default function SmartSearch({ query, setQuery, onSearch, loading, data, userEmail, onLogout }: Props) {
  const [accountOpen, setAccountOpen] = useState(false);
  const submit = (event: FormEvent) => { event.preventDefault(); onSearch(); };
  const result = data?.search;
  const availability = result?.faculty_availability || [];
  const readableTime = (slot: string) => slot.replace(' – ', ' to ');
  const isAllDay = (freeSlots: string[]) => freeSlots.length === 1
    && freeSlots[0].replace(' – ', ' to ') === '8:00 AM to 9:30 PM';
  return <section className={`smart-search ${result ? 'smart-search--has-result' : 'smart-search--empty'}`}>
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
        {availability.map(({ faculty, slots }) => <section className="smart-search__faculty" key={faculty}>
          <header>
            <h3>{faculty}</h3>
            <p>Free during university hours</p>
          </header>
          <div className="smart-search__days">
            {Object.entries(slots)
              .sort(([left], [right]) => WEEKDAY_ORDER.indexOf(left) - WEEKDAY_ORDER.indexOf(right))
              .map(([day, freeSlots]) => <div className="smart-search__day" key={`${faculty}-${day}`}>
                <strong>{day}</strong>
                {freeSlots.length > 0
                  ? <div className="smart-search__slots">
                    {isAllDay(freeSlots)
                      ? <span><b>All day</b><small>8:00 AM to 9:30 PM</small></span>
                      : freeSlots.map((slot, index) => <span key={slot}>{freeSlots.length > 1 && <i>{index + 1}</i>}{readableTime(slot)}</span>)}
                  </div>
                  : <span className="smart-search__none">No free time</span>}
              </div>)}
          </div>
        </section>)}
      </div> : <p>{result.answer}</p>}
    </div>}
  </section>;
}
