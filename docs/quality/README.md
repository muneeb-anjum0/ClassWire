# Quality Suite

ClassWire treats timetable extraction and natural-language search as correctness-critical. A plausible result is still wrong if it includes the wrong section, weekday, faculty member, course type, or credit value. The suite therefore checks exact rows, contracts, and state transitions instead of relying on snapshots alone.

## Suite structure

```text
backend/tests/
├── unit/          Parser, search, cache, normalization, limits, and runtime behavior
├── integration/   API, Gmail, Firestore, security, deletion, and delivery contracts
├── acceptance/    Parsing data, semantic queries, and NLU dataset guarantees
└── fixtures/      Small anonymized or synthetic timetable examples

frontend/src/tests/
├── account-data-cleanup.test.ts
├── account-domain-policy.test.ts
├── api-client-contract.test.ts
├── authentication-flow.test.ts
├── dashboard-controller-behavior.test.tsx
├── initial-page-shell.test.ts
├── large-timetable-rendering.test.tsx
├── login-screen-presentation.test.tsx
├── schedule-feedback-presentation.test.tsx
├── search-suggestion-rotation.test.ts
├── smart-search-experience.test.tsx
├── social-science-dashboard.test.tsx
├── social-science-filtering.test.tsx
├── timetable-course-titles.test.tsx
└── timetable-day-headers.test.tsx
```

Test names describe user-visible behavior. A failing path should make the broken guarantee apparent before reading the implementation.

## Current inventory

| Layer | Checks | Purpose |
| --- | ---: | --- |
| Backend unit | 94 | Small deterministic checks around one behavior |
| Backend integration | 53 | Contracts between layers and controlled service doubles |
| Backend acceptance | 72 | Exact parser output, end-user queries, and NLU data guarantees |
| Frontend behavior | 58 | Browser-like API, state, interaction, persistence, and presentation behavior |
| **Total** | **277** | One coherent regression suite |

## Backend guarantees

- reordered, missing, flattened, malformed, and duplicate timetable rows;
- exact theory `(1,0)`, lab `(0,1)`, and FYP `(0,3)` semantics;
- aliases, compact names, honorifics, spelling errors, and ambiguous faculty identities;
- exact course-to-section binding in custom schedules;
- structural base-section inference, reordered clauses, and explicit course exclusions;
- multi-day filtering, relative weekdays, availability windows, and overlap conflicts;
- latest-per-weekday Gmail selection and unchanged-message reuse;
- compact Firestore payloads, stable hashes, stale-source recovery, and cache behavior;
- authentication boundaries, headers, token encryption, rate limits, and account deletion;
- API response shapes, compression, request tracing, and daily delivery;
- Gunicorn binding and production configuration behavior.
- optional NLU schema, lazy-artifact behavior, routing policy, exact spans, data reproducibility, and split isolation.

## NLU quality gates

The Kaggle pipeline adds model-specific checks without weakening the deterministic suite:

- every labeled entity points to its exact source substring;
- duplicate queries and template-family leakage are rejected;
- every supported intent and entity role appears in training and held-out test data;
- intent accuracy, exact-span entity precision, recall, F1, and joint exact match are recorded;
- deployable artifacts must reach 96% intent accuracy, 94% exact-span entity F1, and 85% whole-query joint exact match;
- quantized artifact size, cold load time, CPU latency percentiles, and peak resident memory are recorded;
- export fails its final benchmark unless the configured accuracy, latency, and size gates pass.

Generated model measurements are not committed as claims. A reviewed Kaggle report must accompany any production artifact update.

## Frontend guarantees

- native Fetch credentials, JSON contracts, timeouts, and structured failures;
- stale-request protection and last-successful-result preservation;
- accessible search, result visibility, and account controls;
- persistent non-SZABIST account warnings;
- recent and suggested query rotation;
- bounded rendering for large result sets;
- chronological desktop and mobile timetable ordering;
- section and room badge presentation;
- connected conflict grouping and red diagonal clash treatment;
- suppression of false clash styling for broad and faculty results;
- search feedback spacing and presentation;
- Social Sciences normalization and lab-title display;
- browser data cleanup during permanent account deletion;
- an intentionally styled initial page shell without an unstyled text flash;
- private-browser OAuth handoff, same-origin API routing, and popup-free authentication.

## Acceptance policy

The semantic query matrix covers common, misspelled, compact, additive, negative, reordered, ambiguous, and multi-constraint requests. It includes paraphrase families for base schedules, course-section bindings, exclusions, faculty availability, and relative dates. Every case asserts the complete expected identity set and rejects unexpected rows. This is essential because overmatching can look convincing while producing an unusable timetable.

Parser acceptance fixtures use explicit expected rows for representative HTML and text formats. Fixtures contain anonymized or synthetic data only.

## Running verification

From the repository root:

```bash
backend/.venv/bin/python -m pytest
backend/.venv/bin/python -m pytest -m unit
backend/.venv/bin/python -m pytest -m integration
backend/.venv/bin/python -m pytest -m acceptance
backend/.venv/bin/python -m pytest --cov=backend --cov-report=term-missing
python tools/repository_guard.py
```

From `frontend/`:

```bash
npm test
npm run test:watch
npm run test:coverage
npm run build
```

## Coverage policy

Backend coverage uses branch tracking and has a repository-wide floor of 61%. Frontend coverage has independent statement, branch, function, and line floors. Current measured baselines are 64.2% backend branch-aware coverage and 73.8% frontend line coverage.

Coverage is a guardrail, not a replacement for exact behavioral assertions. Reports are generated locally and in CI but are not committed.

## Test design rules

1. Name the behavior and expected outcome.
2. Assert both missing and unexpected rows for search acceptance cases.
3. Use deterministic doubles for Gmail, Firestore, Google OAuth, email delivery, and network boundaries.
4. Never require production credentials or a real user account.
5. Keep fixtures anonymized or synthetic.
6. Pass an explicit reference date or mocked clock into time-dependent behavior.
7. Reproduce a regression with the smallest input that demonstrates it.
8. Prefer contract and behavior assertions over implementation snapshots.
9. Run both responsive timetable representations when presentation logic is shared.
10. Update published counts only after the complete suite succeeds.

## Continuous integration

Every pull request and push to `main` runs:

1. repository secret and structure checks;
2. Python dependency audit;
3. the complete backend suite with coverage;
4. npm dependency audit;
5. the complete frontend suite with coverage;
6. TypeScript verification and the production Vite build.

The CI commands match the documented local commands, so a local pass and a protected-branch pass evaluate the same quality boundaries.

[Back to documentation index](../README.md)
