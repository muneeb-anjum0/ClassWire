# ClassWire

I built ClassWire because my university timetable arrived as a messy Gmail message. I wanted to sign in once, extract only my semesters, and see a clean schedule without rebuilding it by hand every time.

## Ideology

My rule for this project is simple: automation should remove boring work without hiding how it works. I prefer a small, readable system with explicit security boundaries over clever code that becomes difficult to trust or maintain.

## Process

I began with an email scraper and a table. The real work appeared when timetable emails changed shape, section labels became inconsistent, and Google OAuth behaved differently on localhost and production. I handled that with structured and fallback parsing, moved persistence from Supabase to Firestore, replaced browser-trusted identity with signed server sessions, and encrypted stored Gmail credentials.

The biggest barriers were OAuth consent and redirect rules, safely separating each user's data, and reducing an overgrown frontend without changing its behavior. Those problems pushed the project toward the modular structure it has now rather than becoming a pile of one-off fixes.

ClassWire now provides:

- Gmail OAuth and read-only timetable discovery
- Per-user semester filters and cached schedules
- A responsive light/dark dashboard
- Optional SMTP delivery to a personal inbox
- Encrypted OAuth credentials in Firestore

## Run locally

```powershell
# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
python backend\app.py

# Frontend, in another terminal
cd frontend
npm ci
Copy-Item .env.example .env
npm run dev
```

The frontend runs at `http://localhost:5173` and the API at `http://localhost:5000`. Add the frontend URL to `FRONTEND_ORIGINS` and to the Google OAuth client configuration.

## Configuration

Use [backend/.env.example](backend/.env.example) and [frontend/.env.example](frontend/.env.example) as the source of truth. Never commit `.env`, Firebase service-account JSON, OAuth client JSON, app passwords, or refresh tokens.

Setup details:

- [Firebase and Firestore](docs/firebase-setup.md)
- [Google OAuth](docs/google-oauth-localhost.md)
- [Project layout](docs/project-structure.md)

## Verify

```powershell
.\.venv\Scripts\python.exe tools\repository_guard.py
.\.venv\Scripts\python.exe -m pytest backend\tests
.\.venv\Scripts\pip-audit.exe --local
cd frontend
npm test
npm run build
npm audit
```

I intentionally keep the frontend away from Firestore. All database access goes through Flask, authenticated requests use signed HTTP-only sessions, and stored Gmail tokens are encrypted before being written to Firestore. CI also rejects unexpected root files, tracked credentials, private keys, symlinks, executables, and vulnerable dependencies before deployment.

For that protection to be enforceable, the GitHub `main` branch should require the **Security and quality** check and a CODEOWNER review. Render should use `backend` as its root directory and `gunicorn app:app` as its start command.
