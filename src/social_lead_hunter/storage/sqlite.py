from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from social_lead_hunter.models import QualificationResult, SocialPost


class SQLiteStorage:
    def __init__(self, path: str):
        self.path = path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    text TEXT NOT NULL,
                    permalink TEXT NOT NULL,
                    post_timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, external_id)
                );
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    reasons TEXT NOT NULL,
                    draft_reply TEXT,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, external_id)
                );
                CREATE TABLE IF NOT EXISTS replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    reply_id TEXT NOT NULL,
                    replied_at TEXT NOT NULL
                );
                """
            )

    def has_post(self, platform: str, external_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM posts WHERE platform=? AND external_id=? LIMIT 1", (platform, external_id)).fetchone()
            return row is not None

    def save_raw_post(self, platform: str, external_id: str, username: str, text: str, permalink: str, timestamp: datetime) -> None:
        ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO posts(platform, external_id, username, text, permalink, post_timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (platform, external_id, username, text, permalink, ts.astimezone(timezone.utc).isoformat()),
            )

    def count_posts(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0])

    def save_candidate(self, post: SocialPost, result: QualificationResult, draft_reply: str | None, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO leads(platform, external_id, username, score, reasons, draft_reply, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(platform, external_id) DO UPDATE SET
                    score=excluded.score,
                    reasons=excluded.reasons,
                    draft_reply=excluded.draft_reply,
                    status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (post.platform, post.external_id, post.username, result.score, " | ".join(result.reasons), draft_reply, status),
            )

    def mark_replied(self, platform: str, external_id: str, reply_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            lead = conn.execute("SELECT username FROM leads WHERE platform=? AND external_id=?", (platform, external_id)).fetchone()
            username = lead["username"] if lead else "unknown"
            conn.execute("UPDATE leads SET status='replied', updated_at=CURRENT_TIMESTAMP WHERE platform=? AND external_id=?", (platform, external_id))
            conn.execute(
                "INSERT INTO replies(platform, external_id, username, reply_id, replied_at) VALUES (?, ?, ?, ?, ?)",
                (platform, external_id, username, reply_id, now),
            )

    def last_reply_to_user(self, username: str) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute("SELECT replied_at FROM replies WHERE lower(username)=lower(?) ORDER BY replied_at DESC LIMIT 1", (username,)).fetchone()
        return datetime.fromisoformat(row[0]) if row else None

    def replies_since(self, since: datetime) -> list[datetime]:
        since_utc = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
        with self._connect() as conn:
            rows = conn.execute("SELECT replied_at FROM replies WHERE replied_at >= ? ORDER BY replied_at ASC", (since_utc.astimezone(timezone.utc).isoformat(),)).fetchall()
        return [datetime.fromisoformat(row[0]) for row in rows]
