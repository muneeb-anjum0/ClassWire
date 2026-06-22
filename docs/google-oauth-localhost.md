# Google OAuth Localhost Setup

## Main goal

Your Google OAuth client must allow the local frontend and the local backend callback.

## 1. Open the right Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Select the project that owns your Gmail API credentials.

## 2. Check the OAuth consent screen

1. Open `APIs & Services -> OAuth consent screen`.
2. Make sure the app is configured.
3. If the app is still in testing mode, add your Gmail account under `Test users`.

## 3. Update the OAuth client

1. Open `APIs & Services -> Credentials`.
2. Open the OAuth 2.0 client used by ClassWire.
3. Add these Authorized redirect URIs:

```text
http://localhost:5000/api/auth/gmail/callback
http://127.0.0.1:5000/api/auth/gmail/callback
```

4. Add these Authorized JavaScript origins if you are using a `web` client:

```text
http://localhost:5173
http://127.0.0.1:5173
```

## 4. Download the updated client JSON

1. Download the OAuth client JSON again after saving.
2. Put it into one of these backend env values:

- `CLIENT_SECRET_JSON`
- or a local file at `backend/credentials/client_secret.json`

## 5. Local env values that should match

In [backend/.env](D:/Desktop/Inbox2table/backend/.env):

```env
PUBLIC_BACKEND_URL=http://localhost:5000
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

In [frontend/.env](D:/Desktop/Inbox2table/frontend/.env):

```env
VITE_API_URL=http://localhost:5000
```

## 6. Restart after changes

After editing Google credentials or env files:

1. Stop the Flask backend.
2. Start it again with `python app.py`.
3. Restart the React dev server with `npm run dev`.

## 7. Common localhost errors

- `redirect_uri_mismatch`
  The callback URL in Google Cloud does not exactly match `http://localhost:5000/api/auth/gmail/callback`.

- `ERR_CONNECTION_REFUSED`
  The frontend is pointing at `localhost:5000`, but the backend is not running.

- Gmail popup closes immediately
  Check the backend terminal and the browser console. Most often this is either redirect URI mismatch or a missing `CLIENT_SECRET_JSON`.
