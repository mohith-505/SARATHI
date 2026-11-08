from __future__ import annotations

from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from connectors.google.auth import get_credentials
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    max_results: int = Field(5, description="Maximum number of emails to retrieve.")
    query: str = Field(
        "is:unread",
        description="Gmail search query (e.g., 'is:unread', 'from:boss').",
    )


class GmailReadTool(Tool):
    name = "gmail_read"
    description = "Read recent emails from Gmail. Returns subject, sender, and snippet."
    permission_level = PermissionLevel.T1
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        creds = get_credentials(scopes)

        if not creds or not creds.valid:
            return ToolResult(
                success=False,
                error="Not authenticated with Google. Please run 'sarathi connect gdrive'."
            )

        try:
            service = build('gmail', 'v1', credentials=creds)
            results = service.users().messages().list(
                userId='me', q=args.query, maxResults=args.max_results
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return ToolResult(success=True, output={"emails": []})

            emails = []
            for msg in messages:
                msg_data = service.users().messages().get(
                    userId='me', id=msg['id'], format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()

                headers = msg_data.get('payload', {}).get('headers', [])
                subject = next(
                    (h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)'
                )
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '(Unknown)')
                snippet = msg_data.get('snippet', '')

                emails.append({
                    "id": msg['id'],
                    "date": date,
                    "from": sender,
                    "subject": subject,
                    "snippet": snippet
                })

            return ToolResult(success=True, output={"emails": emails})

        except Exception as e:
            return ToolResult(success=False, error=f"Gmail API error: {e}")
