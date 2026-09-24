# Search Engine

ClassWire uses a deterministic timetable interpreter rather than sending every question to a paid language model. The engine builds an inspectable query plan, executes it against normalized rows, and returns both a readable answer and the exact matching classes.

## Guarded semantic fallback

ClassWire now includes a complete offline pipeline for an optional compact TinyBERT model. The model predicts one request intent and BIO-tagged semantic roles. It is deliberately outside the database and execution path: it cannot return classes, invent catalog values, or bypass the query planner.

The rollout contract is conservative:

1. The deterministic interpreter runs first.
2. A confident deterministic plan is used without model inference.
3. Only unresolved or ungrounded language can consult the optional model.
4. Model output must pass its confidence threshold and typed span validation.
5. Predicted text is grounded against the current timetable catalog.
6. Ambiguous or unsupported values produce clarification or no result rather than a broad guess.

The production backend continues to work normally when no model artifact is installed. Training happens offline on Kaggle, while Render receives only the tested INT8 ONNX package and lightweight inference libraries. The full workflow and acceptance gates are documented in the [NLU training pipeline](../../ml/query_understanding/README.md).

## Recognized dimensions

- weekdays, including `today`, `tomorrow`, and `yesterday` in Pakistan time;
- complete-week requests and broad schedule intent;
- semester and section variations;
- faculty names, titles, common short forms, and limited spelling mistakes;
- course titles and compact or spaced course codes;
- theory, lab, and FYP class types;
- numeric and written credit-hour values;
- base-section and course-section relationships expressed in varied sentence structures;
- positive additions and negative constraints such as `except`, `without`, `skip`, and `I don't take`.

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
| Exclusions | Course titles or codes explicitly removed from the base schedule |
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

Custom schedules are inferred from entity relationships, not only trigger words. Explicit language such as `plus` and `include` is supported, but the planner can also recognize a base section and a separately bound course in sentences such as `Class of BSSE7A and Software Construction with BSSE5B today`.

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

## Exclusions and clause scope

Negative clauses are compiled separately from positive selections. In `every BSSE7A class except Software Re-Engineering, with Software Construction from BSSE5B`, the excluded course is removed only after the complete base timetable and bound addition have been assembled. It is never reinterpreted as another requested course.

The interpreter recognizes common negative forms including `except`, `excluding`, `without`, `but not`, `other than`, `leave out`, `skip`, `remove`, `I don't take`, and `I do not take`. Course codes and titles use the same exclusion path.

## Faculty availability

Availability is calculated from occupied class intervals within configured university hours.

1. Matching classes are grouped by faculty and day.
2. Time strings are converted into minute intervals.
3. Overlapping or adjacent occupied intervals are merged.
4. Gaps between the day boundary and merged occupied intervals become free slots.
5. Multi-faculty questions keep separate identities and separate schedules.

Supporting class rows are returned with the calculated availability so the answer can be checked.

## Clash detection

Only an intentionally composed custom schedule is checked for personal clashes. Course catalogs, FYP searches, faculty schedules, and other broad results can legitimately contain parallel offerings and therefore never receive false red conflict styling.

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
- Unique section shorthand and small section typos resolve conservatively; ambiguous shorthand remains unresolved instead of being guessed.
- Exact entities do not suppress fuzzy resolution of another entity in the same sentence, so an exact section can still be combined with a misspelled course.
- Common weekday abbreviations, relative days, and bounded weekday typos share one canonical day scope.
- Course-local theory and lab wording remains attached to the relevant custom addition.
- Base sections, bound additions, and exclusions retain separate semantic roles across reordered clauses.
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
- negative course constraints across varied wording and clause order;
- structural base-plus-addition inference without canned additive verbs;
- ordinary parallel results that must not be presented as personal clashes;
- rejection of every unexpected row.

The optional NLU corpus adds independently composed character-span labels, family-isolated train, validation, and test partitions, out-of-scope queries, exact-span entity scoring, joint exact-match scoring, and CPU runtime gates. It does not replace the end-to-end search matrix above.

[Back to documentation index](../README.md)
