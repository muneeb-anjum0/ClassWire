# Firebase Setup

## 1. Create the project

1. Open [Firebase Console](https://console.firebase.google.com/).
2. Create a project for ClassWire.
3. Open `Project settings`.
4. Copy the `Project ID`.

## 2. Enable Firestore

1. Open `Build -> Firestore Database`.
2. Click `Create database`.
3. Start in production mode if you want locked-down rules from day one.
4. Pick the closest region.

## 3. Create a service account

1. Open `Project settings -> Service accounts`.
2. Click `Generate new private key`.
3. Download the JSON file.
4. Either:
   - Save its path in `FIREBASE_SERVICE_ACCOUNT_PATH`, or
   - Paste the full JSON into `FIREBASE_SERVICE_ACCOUNT_JSON`.

## 4. Firestore collections used by the app

ClassWire writes these collections automatically:

- `users`
- `gmail_tokens`
- `user_settings`
- `timetable_cache`

You do not need to create them by hand.

## 5. Backend env values

Add these to [backend/.env](D:/Desktop/Inbox2table/backend/.env):

```env
FLASK_SECRET_KEY=replace-me
TOKEN_ENCRYPTION_KEY=replace-me-with-a-different-long-random-value
PUBLIC_BACKEND_URL=http://localhost:5000
FRONTEND_ORIGINS=http://localhost:5173
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_PATH=C:\path\to\service-account.json
CLIENT_SECRET_JSON={"web":{...}}
AUTOMATION_SECRET=replace-me
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-sender@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_NAME=ClassWire
TZ=Asia/Karachi
GMAIL_QUERY_BASE=subject:("Class Schedule" OR schedule) in:inbox
CHECK_HOUR_LOCAL=20
CHECK_MINUTE_LOCAL=0
NEXT_DAY_AVAILABLE_HOUR=17
NEWER_THAN_DAYS=2
```

## 6. Suggested Firestore rules for a private backend-only app

If only your Flask backend should access Firestore directly, keep the client app out of Firestore entirely and use strict rules like:

```text
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

This works because the backend uses the Firebase Admin SDK, which bypasses client security rules.

The backend encrypts Gmail OAuth payloads before storing them in `gmail_tokens`. Keep `TOKEN_ENCRYPTION_KEY` stable; changing it invalidates previously stored tokens.
