from __future__ import annotations

from datetime import date
from typing import Any

from backend.storage.database import PersistentDatabase


class OutreachTracker:
    def __init__(self, database: PersistentDatabase) -> None:
        self.database = database
        self.logs: list[dict[str, Any]] = []

    def count_sent_today(self, user_id: str) -> int:
        today = date.today().isoformat()
        in_memory = sum(
            1
            for row in self.logs
            if row.get("user_id") == user_id and row.get("sent") and str(row.get("date")) == today
        )
        persisted = self.database.count_sent_today(user_id, today)
        return max(in_memory, persisted)

    def record(
        self,
        user_id: str,
        contact_id: str,
        channel: str,
        sent: bool,
        replied: bool = False,
        positive_reply: bool = False,
    ) -> dict[str, Any]:
        row = {
            "id": f"log-{len(self.logs) + 1}",
            "user_id": user_id,
            "contact_id": contact_id,
            "channel": channel,
            "sent": sent,
            "replied": replied,
            "positive_reply": positive_reply,
            "date": date.today().isoformat(),
        }
        self.logs.append(row)
        self.database.insert_outreach_log(
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "contact_id": row["contact_id"],
                "channel": row["channel"],
                "sent": 1 if row["sent"] else 0,
                "replied": 1 if row["replied"] else 0,
                "positive_reply": 1 if row["positive_reply"] else 0,
                "sent_date": row["date"],
            }
        )
        return row
