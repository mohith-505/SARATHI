"""Google OAuth Connector for SARATHI."""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# The directory where we store the user's tokens and client secrets
CONFIG_DIR = Path.home() / ".sarathi" / "connectors" / "google"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"


def ensure_config_dir() -> None:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_credentials(scopes: list[str]) -> Credentials | None:
    """Get valid user credentials from storage, or None if not authenticated."""
    ensure_config_dir()

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
        except Exception:
            # If the token file is corrupted, ignore it
            pass

    # If there are no (valid) credentials available, let the user log in.
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save the refreshed credentials
            with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        except Exception:
            creds = None

    # Check if the scopes match what we need
    if creds and creds.valid:
        # Check if requested scopes are a subset of granted scopes
        granted = set(creds.scopes or [])
        requested = set(scopes)
        if requested.issubset(granted):
            return creds  # type: ignore[no-any-return]
        else:
            # Need to re-auth for new scopes
            return None

    return creds  # type: ignore[no-any-return]


def authenticate(scopes: list[str], force: bool = False) -> Credentials:
    """Run the OAuth flow to get credentials.

    Requires credentials.json to be placed in CONFIG_DIR.
    """
    ensure_config_dir()

    if not force:
        creds = get_credentials(scopes)
        if creds and creds.valid:
            return creds

    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Google Cloud OAuth client secret not found at {CREDENTIALS_FILE}. "
            "Please create a Desktop App OAuth Client ID in Google Cloud Console, "
            "download the JSON, and save it there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE), scopes
    )
    # Run the local server to catch the callback
    creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open(TOKEN_FILE, "w", encoding="utf-8") as token:
        token.write(creds.to_json())

    return creds  # type: ignore[no-any-return]
