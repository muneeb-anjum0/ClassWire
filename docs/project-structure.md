# Project Structure

## Root

- `backend/` Flask API, Gmail integration, parser, persistence, email delivery
- `frontend/` React dashboard
- `docs/` setup notes for Firebase, OAuth, and maintenance

## Backend

- [backend/app.py](D:/Desktop/Inbox2table/backend/app.py)
  Flask entrypoint, Gmail OAuth flow, health checks, and blueprint registration.
- `backend/core/`
  Shared Flask/bootstrap helpers such as CORS, client-secret loading, temp OAuth state, and public URL resolution.
- `backend/routes/`
  Route groups split by responsibility. User config, scrape, cache, status, and automation endpoints live here.
- `backend/database/`
  Firestore persistence, encrypted OAuth tokens, and default user settings.
- `backend/scraper/`
  Gmail fetch, parser, semester matching, and scrape scheduler.
- `backend/utils/`
  Daily email orchestration and provider-specific sending.
- `backend/tests/`
  Backend and parser coverage.

## Frontend

- [frontend/src/App.tsx](D:/Desktop/Inbox2table/frontend/src/App.tsx)
  Small router shell for legal pages and the authenticated dashboard.
- `frontend/src/features/dashboard/`
  Dashboard state hooks, email actions, quick-actions UI, and filtering helpers.
- `frontend/src/components/`
  Reusable UI pieces such as login, semester manager, status toast, summary cards, and timetable table.
- [frontend/src/context/AuthContext.tsx](D:/Desktop/Inbox2table/frontend/src/context/AuthContext.tsx)
  Server-session restoration and Gmail popup/mobile auth flow.
- [frontend/src/services/api.ts](D:/Desktop/Inbox2table/frontend/src/services/api.ts)
  API client and backend wake/autodetect logic.
- `frontend/src/utils/`
  Semester normalization and course correction helpers.
- [frontend/vite.config.ts](D:/Desktop/Inbox2table/frontend/vite.config.ts)
  Vite build and Vitest configuration.
