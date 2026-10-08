"""
MyMind — Google Calendar integration
Reads upcoming events and free/busy slots for the Plan Agent.

Setup:
  1. https://console.cloud.google.com → New project → Enable Calendar API
  2. APIs & Services → Credentials → Create → OAuth 2.0 Client ID (Desktop app)
  3. Download JSON → save as google_credentials.json in backend/
  4. Visit http://localhost:8001/auth/google → authorize in browser
  5. Token saved automatically to google_token.json
"""
import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")  # allow HTTP on localhost

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "./google_credentials.json")
TOKEN_FILE       = os.getenv("GOOGLE_TOKEN_FILE",       "./google_token.json")
CALENDAR_ID      = os.getenv("GOOGLE_CALENDAR_ID",      "primary")
SCOPES           = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarClient:
    def __init__(self):
        self.credentials_file = CREDENTIALS_FILE
        self.token_file = TOKEN_FILE
        self.calendar_id = CALENDAR_ID
        self._service = None

    # ── Status ────────────────────────────────────────────────────────────────
    @property
    def credentials_exist(self) -> bool:
        return Path(self.credentials_file).exists()

    @property
    def authenticated(self) -> bool:
        if not self.credentials_exist or not Path(self.token_file).exists():
            return False
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            return creds.valid or bool(creds.expired and creds.refresh_token)
        except Exception:
            return False

    @property
    def enabled(self) -> bool:
        return self.authenticated

    # ── Service ───────────────────────────────────────────────────────────────
    def _get_service(self):
        if self._service:
            return self._service
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            Path(self.token_file).write_text(creds.to_json())
        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    # ── Data ─────────────────────────────────────────────────────────────────
    def get_events(self, days: int = 21) -> dict:
        """Return upcoming events and free/busy data for the next N days."""
        if not self.enabled:
            return {"available": False, "events": [], "busy": [], "range_days": days}
        try:
            service = self._get_service()
            now = datetime.now(timezone.utc)
            end = now + timedelta(days=days)
            time_min = now.isoformat()
            time_max = end.isoformat()

            events_resp = service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            ).execute()

            events = [
                {
                    "summary": e.get("summary", "(無標題)"),
                    "start": e["start"].get("dateTime", e["start"].get("date", "")),
                    "end":   e["end"].get("dateTime",   e["end"].get("date", "")),
                }
                for e in events_resp.get("items", [])
            ]

            freebusy_resp = service.freebusy().query(body={
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": self.calendar_id}],
            }).execute()
            busy = freebusy_resp["calendars"].get(self.calendar_id, {}).get("busy", [])

            return {
                "available": True,
                "events": events,
                "busy": busy,
                "range_days": days,
                "today": now.strftime("%Y-%m-%d"),
            }
        except Exception as e:
            self._service = None  # Reset so next call retries auth
            return {"available": False, "error": str(e),
                    "events": [], "busy": [], "range_days": days}

    # ── OAuth ─────────────────────────────────────────────────────────────────
    def start_oauth_flow(self) -> str:
        """Return the Google OAuth authorization URL."""
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=SCOPES,
            redirect_uri="http://localhost:8001/auth/google/callback",
        )
        auth_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        # Persist state AND code_verifier (PKCE) so the callback can restore them
        Path(".oauth_state").write_text(json.dumps({
            "state":         state,
            "code_verifier": getattr(flow, "code_verifier", None),
        }))
        return auth_url

    def handle_oauth_callback(self, authorization_response: str, state: str) -> tuple[bool, str]:
        """Exchange auth code for token and save it. Returns (success, error_msg)."""
        try:
            from google_auth_oauthlib.flow import Flow

            # Restore code_verifier saved during start_oauth_flow
            code_verifier = None
            state_file = Path(".oauth_state")
            if not state_file.exists():
                return False, "No OAuth flow in progress; visit /auth/google first"
            saved = json.loads(state_file.read_text())
            if saved.get("state") != state:
                return False, "OAuth state mismatch"
            code_verifier = saved.get("code_verifier")

            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=SCOPES,
                redirect_uri="http://localhost:8001/auth/google/callback",
                state=state,
            )
            if code_verifier:
                flow.code_verifier = code_verifier

            flow.fetch_token(authorization_response=authorization_response)
            Path(self.token_file).write_text(flow.credentials.to_json())
            self._service = None
            return True, ""
        except Exception as e:
            return False, str(e)

    def status(self) -> dict:
        return {
            "credentials_exist": self.credentials_exist,
            "authenticated": self.authenticated,
        }
