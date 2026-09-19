"""
Gmail API client + helpers.
"""
import base64
import logging
import os
from typing import Dict, Iterable, List, Optional

import httplib2
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

LOGGER = logging.getLogger(__name__)

def get_credentials(token_path: str = "token.json", client_secret_path: str = "credentials/client_secret.json") -> Credentials:
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            LOGGER.info("Refreshing Gmail token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(
                    f"Missing OAuth client file at {client_secret_path}. "
                    f"Download from Google Cloud Console → OAuth 2.0 Client IDs."
                )
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
            LOGGER.info("Saved Gmail token to %s", token_path)
    return creds

def build_service(creds: Credentials):
    timeout = max(5, min(int(os.getenv("GMAIL_API_TIMEOUT_SECONDS", "30")), 120))
    authorized_http = AuthorizedHttp(creds, http=httplib2.Http(timeout=timeout))
    return build("gmail", "v1", http=authorized_http, cache_discovery=False)

def list_messages(service, user_id: str, query: str, max_results: int = 10) -> List[Dict]:
    try:
        resp = service.users().messages().list(userId=user_id, q=query, maxResults=max_results).execute()
        return resp.get("messages", []) or []
    except HttpError as e:
        LOGGER.error("Gmail list error: %s", e)
        raise RuntimeError("Gmail search failed; please retry in a moment") from e


def list_latest_messages_batch(service, user_id: str, queries: Dict[str, str]) -> Dict[str, Dict]:
    """Resolve the newest message for several queries in one HTTP round trip.

    Gmail charges the same quota for a batched request, but batching the six
    weekday searches avoids downloading dozens of full candidate emails just
    to inspect their subjects.
    """
    if not queries:
        return {}

    responses: Dict[str, Dict] = {}
    failed_keys = set()

    def receive(request_id, response, exception):
        if exception is not None:
            LOGGER.warning("Gmail list query failed for %s: %s", request_id, exception)
            failed_keys.add(request_id)
            return
        messages = (response or {}).get("messages") or []
        if messages:
            responses[request_id] = messages[0]

    batch = service.new_batch_http_request(callback=receive)
    for key, query in queries.items():
        batch.add(
            service.users().messages().list(userId=user_id, q=query, maxResults=1),
            request_id=key,
        )
    batch.execute()

    for key in failed_keys:
        messages = list_messages(service, user_id=user_id, query=queries[key], max_results=1)
        if messages:
            responses[key] = messages[0]
    return responses

def get_message(service, user_id: str, msg_id: str) -> Dict:
    return service.users().messages().get(userId=user_id, id=msg_id, format="full").execute()


def get_messages_batch(service, user_id: str, message_ids: Iterable[str]) -> Dict[str, Dict]:
    """Fetch messages in one HTTP batch while preserving per-message failures."""
    unique_ids = list(dict.fromkeys(message_id for message_id in message_ids if message_id))
    if not unique_ids:
        return {}

    messages: Dict[str, Dict] = {}
    failed_ids = set()

    def receive(request_id, response, exception):
        if exception is not None:
            LOGGER.warning("Gmail message fetch failed for %s: %s", request_id, exception)
            failed_ids.add(request_id)
            return
        if response:
            messages[request_id] = response

    batch = service.new_batch_http_request(callback=receive)
    for message_id in unique_ids:
        batch.add(
            service.users().messages().get(userId=user_id, id=message_id, format="full"),
            request_id=message_id,
        )
    batch.execute()
    # Batch requests occasionally fail per part even though the connection is
    # healthy. Retry only failed parts once; never return a silently incomplete
    # week because that produces incorrect availability answers.
    for message_id in failed_ids:
        try:
            messages[message_id] = get_message(service, user_id, message_id)
        except Exception:
            LOGGER.warning("Gmail message retry failed for %s", message_id, exc_info=True)
    unresolved = failed_ids - messages.keys()
    if unresolved:
        raise RuntimeError(f"Could not fetch {len(unresolved)} Gmail timetable message(s); please retry")
    return messages


def _decode_body(data: str) -> str:
    padded = data + ("=" * (-len(data) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="ignore")

def _walk_parts_for_html(payload) -> Optional[str]:
    if not payload:
        return None

    mime_type = payload.get("mimeType")
    body = payload.get("body", {})

    if mime_type == "text/html":
        data = body.get("data")
        if data:
            return _decode_body(data)

    if payload.get("parts"):
        plain_text_fallback = None
        for part in payload.get("parts", []) or []:
            html = _walk_parts_for_html(part)
            if html:
                if "<" in html and ">" in html:
                    return html
                if plain_text_fallback is None:
                    plain_text_fallback = html

        if plain_text_fallback:
            return plain_text_fallback

    if mime_type == "text/plain":
        data = body.get("data")
        if data:
            return _decode_body(data)

    return None

def get_message_html(service, user_id: str, msg_id: str) -> Optional[str]:
    return get_message_html_from_message(get_message(service, user_id, msg_id))


def get_message_html_from_message(msg: Dict) -> Optional[str]:
    payload = msg.get("payload", {})
    return _walk_parts_for_html(payload)


def get_message_subject(msg: Dict) -> str:
    headers = (msg.get("payload") or {}).get("headers") or []
    for header in headers:
        if str(header.get("name") or "").casefold() == "subject":
            return str(header.get("value") or "")
    return ""
