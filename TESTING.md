# ClassWire Quality Suite

ClassWire treats timetable extraction and natural-language search as correctness-critical systems. A result that looks plausible but includes the wrong section, weekday, faculty member, or credit type is still wrong. The quality suite therefore checks exact rows and contracts instead of relying on snapshots alone.

## Suite structure

```text
backend/tests/
├── unit/          Fast, isolated parser, search, cache, filtering, and runtime checks
├── integration/   API, Gmail, Firestore, security, and delivery contracts with controlled doubles
├── acceptance/    Representative parser data and forty end-user search scenarios
└── fixtures/      Small, anonymized timetable examples with explicit expected output

frontend/src/tests/
├── api-client-contract.test.ts
├── dashboard-controller-behavior.test.tsx
├── large-timetable-rendering.test.tsx
├── search-suggestion-rotation.test.ts
├── smart-search-experience.test.tsx
├── social-science-dashboard.test.tsx
├── social-science-filtering.test.tsx
└── timetable-course-titles.test.tsx
```

The names describe behavior rather than implementation details. A failing path should immediately tell a maintainer which user-facing guarantee changed.

| Layer | Current checks | Purpose |
| --- | ---: | --- |
| Backend unit | 104 | Small, deterministic checks around one behavior |
| Backend integration | 53 | Contracts between ClassWire layers and controlled service doubles |
| Backend acceptance | 41 | Exact parser output and end-user natural-language scenarios |
| Frontend behavior | 21 | Browser-like interaction, state, API, and presentation checks |
| **Total** | **219** | One coherent regression suite |

## What is protected

The backend suite checks:

- reordered, missing, flattened, malformed, and duplicated timetable rows;
- exact credit semantics for theory `(1,0)`, labs `(0,1)`, and FYP `(0,3)`;
- aliases, compact names, honorifics, spelling errors, and ambiguous faculty identities;
- course-to-section binding for customized cross-section schedules;
- multi-day filtering, relative weekdays, availability windows, and overlap conflicts;
- latest-per-weekday Gmail selection and reuse of unchanged messages;
- compact Firestore payloads, stable hashes, stale-source recovery, and cache behavior;
- authentication boundaries, security headers, token encryption, rate limiting, and account deletion;
- API response shape, compression, request tracing, and daily-email delivery.

The frontend suite checks:

- native Fetch credentials, JSON requests, timeouts, and structured API failures;
- stale-request protection and preservation of the last successful timetable;
- accessible search interactions and result visibility controls;
- recent and suggested query rotation;
- bounded rendering for large result sets;
- correct Social Sciences grouping and lab-title presentation.

## Running the suite

From the repository root:

```bash
backend/.venv/bin/python -m pytest
backend/.venv/bin/python -m pytest -m unit
backend/.venv/bin/python -m pytest -m integration
backend/.venv/bin/python -m pytest -m acceptance
backend/.venv/bin/python -m pytest --cov=backend --cov-report=term-missing
```

From `frontend/`:

```bash
npm test
npm run test:watch
npm run test:coverage
npm run build
```

## Test design rules

1. Test names state the behavior and expected outcome.
2. Acceptance tests compare exact result identities, including unexpected rows, because overmatching is as dangerous as missing data.
3. Network, Gmail, Firestore, and email-provider calls use deterministic doubles. The suite never requires a real user account or production credentials.
4. Fixtures contain anonymized or synthetic schedule data only.
5. Time-dependent behavior receives an explicit reference date or mocked clock.
6. Regression tests reproduce the smallest input that exposed the defect.
7. Coverage is a guardrail, not a substitute for assertions about behavior.

## Continuous integration

Every pull request and every push to `main` runs repository secret scanning, backend tests with branch coverage, frontend tests with coverage, dependency audits, and the production frontend build. CI uses the same commands documented above, so a local pass has the same meaning as a remote pass.

Coverage reports are generated locally and in CI but are not committed. This keeps the repository clean while making untested paths visible during review.
