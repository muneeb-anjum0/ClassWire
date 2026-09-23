# Search Engine

ClassWire uses a deterministic timetable interpreter rather than sending every question to a paid language model. The engine builds an inspectable query plan, executes it against normalized rows, and returns both a readable answer and the exact matching classes.

## Recognized dimensions

- weekdays, including `today`, `tomorrow`, and `yesterday` in Pakistan time;
- complete-week requests and broad schedule intent;
- semester and section variations;
- faculty names, titles, common short forms, and limited spelling mistakes;
- course titles and compact or spaced course codes;
- theory, lab, and FYP class types;
- numeric and written credit-hour values;
- additive language used to build cross-section schedules.

Formatting-only variants resolve to canonical identities. Faculty matching remains conservative: a short or ambiguous name is not silently merged into a longer, different identity.

## Query plan

Every recognized request produces a plan containing:

| Plan field | Purpose |
| --- | --- |
| Intent | Schedule search or faculty free-time calculation |
| Day scope | One day, multiple days, relative day, or the entire week |
| Combination | Intersection for normal filtering or union for custom schedules |
| Sections | Canonical requested section identities |
| Courses and codes | Requested titles and catalog codes |
| Base section | Complete timetable to retain in a custom schedule |
| Course-section bindings | Exact course or code additions from exact requested sections |
| Local class type | Theory, lab, or FYP qualifier attached to a specific addition |
| Global filters | Credit and class-type constraints applied to the complete result |
| Faculty | One or more canonical faculty identities |

Returning this plan makes overmatching and missing constraints diagnosable.

## Intersection searches

Normal requests combine recognized filters with intersection semantics.

```text
Question
  Show Software Construction and Development for BSSE5A on Monday

Plan
  day: Monday
  section: BS(SE)-5A
  course: Software Construction and Development
  combination: intersection

Result
  Only matching Monday rows from BS(SE)-5A
```

Course, code, faculty, weekday, section, class type, and credit constraints must all match when they appear together.

## Custom schedule unions

Additive phrases such as `plus`, `also`, `along with`, `as well`, and `I am from ... but want to take ...` produce union plans.

```text
Question
  I am from BSSE7A; add Software Construction theory from BSSE5B
  and Software Quality Engineering from BSSE6A

Plan
  base section: BS(SE)-7A
  addition 1: Software Construction, theory, BS(SE)-5B
  addition 2: Software Quality Engineering, BS(SE)-6A
  combination: union

Result
  Complete BS(SE)-7A timetable plus only the two bound additions
```

Each addition keeps its own section and class-type qualifier. A course name and its code refer to one selection rather than creating duplicate rows.

## Faculty availability

Availability is calculated from occupied class intervals within configured university hours.

1. Matching classes are grouped by faculty and day.
2. Time strings are converted into minute intervals.
3. Overlapping or adjacent occupied intervals are merged.
4. Gaps between the day boundary and merged occupied intervals become free slots.
5. Multi-faculty questions keep separate identities and separate schedules.

Supporting class rows are returned with the calculated availability so the answer can be checked.

## Clash detection

Custom schedule rows are grouped by weekday and sorted by start time. Every overlapping pair records:

- weekday;
- exact overlap interval;
- both course titles;
- both sections;
- both original time ranges.

The client builds connected conflict groups from these pairs. Conflicting rows are placed next to each other, marked with a restrained red diagonal pattern, and enclosed as a single visual block on desktop and mobile. A connected three-class collision therefore remains one group rather than three unrelated warnings.

## Matching safeguards

- Exact normalized identities take priority over fuzzy candidates.
- Fuzzy matching is bounded to avoid unrelated course and faculty results.
- Section normalization tolerates spacing and punctuation without discarding the section letter.
- Course-local theory and lab wording remains attached to the relevant custom addition.
- Credit tuples preserve separate theory and practical components.
- Duplicate rows are removed before the final count.
- Relative weekdays receive an explicit reference date in tests.
- Unrecognized questions return a clear response instead of an unbounded result set.

## Search caching

Repeated queries use a bounded result cache keyed by user, normalized question, parser version, and source identity. Changing the timetable source or parser version invalidates the old answer automatically. A warm repeated query measured approximately 0.001 ms locally for cache retrieval; this is a local micro-benchmark, not an end-to-end network latency claim.

## Representative coverage

The acceptance matrix includes exact assertions for:

- single-section and multi-section days;
- course names and course codes;
- theory, lab, FYP, and credit filters;
- misspelled weekdays, compact names, and aliases;
- faculty classes and multi-person availability;
- full-week and relative-day requests;
- base timetables with one or more course-section additions;
- independently bound theory and lab choices;
- conflict-producing schedules;
- rejection of every unexpected row.

[Back to documentation index](../README.md)
