"""SQLite persistence for Playlist Assistant application settings and status.

This module is deliberately independent of Home Assistant and Spotify.  It
uses the existing production database while keeping SQL out of the runtime and
future application UI layers.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Optional
from contextlib import contextmanager

from runtime_config import RuntimeConfig


DEFAULT_DB_PATH = Path("playlist_assistant.db")


@dataclass(frozen=True)
class JobStatus:
    """Serializable last-completion status for one finite runtime job."""

    job_name: str
    started_at: str
    ended_at: str
    duration_seconds: float
    success: bool
    failed_step: Optional[str]
    error_type: Optional[str]
    error_message: Optional[str]
    last_success_at: Optional[str]

    def to_dict(self) -> dict:
        """Return a Home-Assistant-independent serializable representation."""
        return asdict(self)


class ApplicationStorage:
    """Read and write application-owned data in the production SQLite file."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self._db_path = Path(db_path or DEFAULT_DB_PATH)

    def load_runtime_config(self) -> RuntimeConfig:
        """Return persisted settings, falling back to ``RuntimeConfig`` defaults."""
        with self._connection() as conn:
            self._ensure_schema(conn)
            values = {
                row[0]: int(row[1])
                for row in conn.execute(
                    """
                    SELECT setting_name, setting_value FROM application_setting
                    WHERE setting_name IN (
                        'today_size', 'rare_weight', 'artist_min_gap',
                        'history_poll_minutes'
                    )
                    """
                )
            }
        return RuntimeConfig(**values)

    def save_runtime_config(self, config: RuntimeConfig) -> None:
        """Persist the configurable RuntimeConfig values after central validation."""
        with self._connection() as conn:
            self._ensure_schema(conn)
            conn.executemany(
                """
                INSERT INTO application_setting (setting_name, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_name) DO UPDATE SET setting_value = excluded.setting_value
                """,
                (
                    ("today_size", config.today_size),
                    ("rare_weight", config.rare_weight),
                    ("artist_min_gap", config.artist_min_gap),
                    ("history_poll_minutes", config.history_poll_minutes),
                ),
            )

    def record_job_result(self, result) -> JobStatus:
        """Persist a completed runtime result without retaining its exception object."""
        error = result.error
        status = JobStatus(
            job_name=result.job_name,
            started_at=_serialize_datetime(result.started_at),
            ended_at=_serialize_datetime(result.ended_at),
            duration_seconds=result.duration_seconds,
            success=result.success,
            failed_step=result.failed_step,
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            last_success_at=_serialize_datetime(result.ended_at)
            if result.success
            else None,
        )
        with self._connection() as conn:
            self._ensure_schema(conn)
            previous = self.get_job_status(result.job_name, conn=conn)
            last_success_at = status.last_success_at or (
                previous.last_success_at if previous else None
            )
            status = JobStatus(
                **{**status.to_dict(), "last_success_at": last_success_at}
            )
            conn.execute(
                """
                INSERT INTO application_job_status (
                    job_name, started_at, ended_at, duration_seconds, success,
                    failed_step, error_type, error_message, last_success_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_name) DO UPDATE SET
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    duration_seconds = excluded.duration_seconds,
                    success = excluded.success,
                    failed_step = excluded.failed_step,
                    error_type = excluded.error_type,
                    error_message = excluded.error_message,
                    last_success_at = excluded.last_success_at
                """,
                (
                    status.job_name,
                    status.started_at,
                    status.ended_at,
                    status.duration_seconds,
                    int(status.success),
                    status.failed_step,
                    status.error_type,
                    status.error_message,
                    status.last_success_at,
                ),
            )
        return status

    def get_job_status(
        self, job_name: str, *, conn: sqlite3.Connection | None = None
    ) -> Optional[JobStatus]:
        """Load the last stored status for ``history`` or ``today``."""
        if conn is None:
            with self._connection() as local_conn:
                self._ensure_schema(local_conn)
                return self.get_job_status(job_name, conn=local_conn)
        row = conn.execute(
            """
            SELECT job_name, started_at, ended_at, duration_seconds, success,
                   failed_step, error_type, error_message, last_success_at
            FROM application_job_status WHERE job_name = ?
            """,
            (job_name,),
        ).fetchone()
        if row is None:
            return None
        return JobStatus(
            job_name=row[0],
            started_at=row[1],
            ended_at=row[2],
            duration_seconds=row[3],
            success=bool(row[4]),
            failed_step=row[5],
            error_type=row[6],
            error_message=row[7],
            last_success_at=row[8],
        )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS application_setting (
                setting_name TEXT PRIMARY KEY,
                setting_value INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS application_job_status (
                job_name TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                success INTEGER NOT NULL CHECK (success IN (0, 1)),
                failed_step TEXT,
                error_type TEXT,
                error_message TEXT,
                last_success_at TEXT
            )
            """
        )


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()
