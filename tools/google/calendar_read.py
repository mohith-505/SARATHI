from __future__ import annotations

from datetime import UTC, datetime

from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from connectors.google.auth import get_credentials
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    max_results: int = Field(10, description="Maximum number of upcoming events to retrieve.")


class CalendarReadTool(Tool):
    name = "calendar_read"
    description = "Read upcoming events from Google Calendar."
    permission_level = PermissionLevel.T1
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
        creds = get_credentials(scopes)

        if not creds or not creds.valid:
            return ToolResult(
                success=False,
                error="Not authenticated with Google. Please run 'sarathi connect gdrive'.",
            )

        try:
            service = build("calendar", "v3", credentials=creds)
            now = datetime.now(UTC).isoformat()

            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=args.max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])
            if not events:
                return ToolResult(success=True, output={"events": []})

            upcoming = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                upcoming.append({
                    "id": event["id"],
                    "summary": event.get("summary", "(No title)"),
                    "start": start,
                    "end": end,
                    "link": event.get("htmlLink", ""),
                })

            return ToolResult(success=True, output={"events": upcoming})

        except Exception as e:
            return ToolResult(success=False, error=f"Calendar API error: {e}")
