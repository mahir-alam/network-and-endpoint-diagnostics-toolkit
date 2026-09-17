"""
Layer 1 - Uptime/downtime history.

Persists every reachability check to a local SQLite database so uptime
percentage can be computed across monitoring runs over time, not just from
the single most recent check.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from layer1_network_monitor.network_scanner import CheckResult

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "logs" / "uptime_history.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    reachable INTEGER NOT NULL,
    method TEXT NOT NULL,
    latency_ms REAL,
    detail TEXT,
    checked_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checks_hostname ON checks (hostname);
"""


class UptimeTracker:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record(self, result: CheckResult) -> None:
        self._conn.execute(
            """INSERT INTO checks (hostname, ip_address, reachable, method, latency_ms, detail, checked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                result.hostname,
                result.ip_address,
                1 if result.reachable else 0,
                result.method,
                result.latency_ms,
                result.detail,
                result.checked_at,
            ),
        )
        self._conn.commit()

    def record_all(self, results: list[CheckResult]) -> None:
        for result in results:
            self.record(result)

    def uptime_percent(self, hostname: str) -> float | None:
        cursor = self._conn.execute(
            "SELECT COUNT(*), SUM(reachable) FROM checks WHERE hostname = ?",
            (hostname,),
        )
        total, up = cursor.fetchone()
        if not total:
            return None
        up = up or 0
        return round((up / total) * 100, 1)

    def check_count(self, hostname: str) -> int:
        cursor = self._conn.execute("SELECT COUNT(*) FROM checks WHERE hostname = ?", (hostname,))
        return cursor.fetchone()[0]

    def last_status_change(self, hostname: str) -> str | None:
        """Timestamp of the most recent check where status differs from the one before it."""
        cursor = self._conn.execute(
            "SELECT reachable, checked_at FROM checks WHERE hostname = ? ORDER BY id DESC",
            (hostname,),
        )
        rows = cursor.fetchall()
        if len(rows) < 2:
            return rows[0][1] if rows else None
        current_status = rows[0][0]
        for reachable, checked_at in rows[1:]:
            if reachable != current_status:
                return rows[0][1]
        return rows[-1][1]

    def close(self) -> None:
        self._conn.close()
