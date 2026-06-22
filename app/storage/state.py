from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class StateStore:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_issues (
                    issue_id INTEGER PRIMARY KEY,
                    issue_updated_on TEXT,
                    project_identifier TEXT,
                    last_processed_at TEXT,
                    last_comment_hash TEXT,
                    status TEXT,
                    error_message TEXT
                )
                """
            )

    def is_already_processed(self, issue_id: int, issue_updated_on: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT issue_updated_on, status FROM processed_issues WHERE issue_id = ?",
                (issue_id,),
            ).fetchone()
        return bool(row and row[0] == issue_updated_on and row[1] == "success")

    def mark_processed(self, issue_id: int, issue_updated_on: str, project_identifier: str, comment_hash: str) -> None:
        self._upsert(issue_id, issue_updated_on, project_identifier, comment_hash, "success", None)

    def mark_failed(self, issue_id: int, issue_updated_on: str, project_identifier: str, error_message: str) -> None:
        self._upsert(issue_id, issue_updated_on, project_identifier, "", "failed", error_message)

    def _upsert(
        self,
        issue_id: int,
        issue_updated_on: str,
        project_identifier: str,
        comment_hash: str,
        status: str,
        error_message: str | None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO processed_issues (
                    issue_id, issue_updated_on, project_identifier, last_processed_at,
                    last_comment_hash, status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(issue_id) DO UPDATE SET
                    issue_updated_on = excluded.issue_updated_on,
                    project_identifier = excluded.project_identifier,
                    last_processed_at = excluded.last_processed_at,
                    last_comment_hash = excluded.last_comment_hash,
                    status = excluded.status,
                    error_message = excluded.error_message
                """,
                (issue_id, issue_updated_on, project_identifier, now, comment_hash, status, error_message),
            )
