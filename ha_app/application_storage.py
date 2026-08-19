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

from application_paths import ApplicationPaths
from runtime_config import RuntimeConfig


DEFAULT_DB_PATH = ApplicationPaths.default().database_path


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


@dataclass(frozen=True)
class SchedulerState:
    """Persistent scheduler-owned attempt state, separate from job status."""

    last_history_attempt_at: Optional[str]
    last_today_attempt_date: Optional[str]


@dataclass(frozen=True)
class PreviewState:
    fingerprint: str
    created_at: str


class ApplicationStorage:
    """Read and write application-owned data in the production SQLite file."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self._db_path = Path(db_path or DEFAULT_DB_PATH)

    def load_runtime_config(self) -> RuntimeConfig:
        """Return persisted settings, falling back to ``RuntimeConfig`` defaults."""
        with self._connection() as conn:
            self._ensure_schema(conn)
            raw_values = {
                row[0]: row[1]
                for row in conn.execute(
                    """
                    SELECT setting_name, setting_value FROM application_setting
                    WHERE setting_name IN (
                        'today_size', 'rare_weight', 'artist_gap',
                        'history_poll_minutes', 'today_schedule_enabled',
                        'today_schedule_time'
                    )
                    """
                )
            }
        values = {
            "today_size": int(raw_values["today_size"])
            if "today_size" in raw_values else None,
            "rare_weight": int(raw_values["rare_weight"])
            if "rare_weight" in raw_values else None,
            "artist_gap": int(raw_values["artist_gap"])
            if "artist_gap" in raw_values else None,
            "history_poll_minutes": int(raw_values["history_poll_minutes"])
            if "history_poll_minutes" in raw_values else None,
            "today_schedule_enabled": _deserialize_bool(raw_values["today_schedule_enabled"])
            if "today_schedule_enabled" in raw_values else None,
            "today_schedule_time": str(raw_values["today_schedule_time"])
            if "today_schedule_time" in raw_values else None,
        }
        values = {name: value for name, value in values.items() if value is not None}
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
                    ("artist_gap", config.artist_gap),
                    ("history_poll_minutes", config.history_poll_minutes),
                    ("today_schedule_enabled", int(config.today_schedule_enabled)),
                    ("today_schedule_time", config.today_schedule_time),
                ),
            )

    def get_target_playlist(self) -> tuple[str, str | None]:
        """Return the configured target name and its persisted Spotify ID."""
        with self._connection() as conn:
            self._ensure_schema(conn)
            values = dict(conn.execute(
                "SELECT setting_name, setting_value FROM application_setting "
                "WHERE setting_name IN ('target_playlist_name', 'target_playlist_id')"
            ))
        return values.get("target_playlist_name", "Playlist Assistant"), values.get("target_playlist_id")

    def save_target_playlist(self, name: str, playlist_id: str | None = None) -> None:
        """Persist target identity; a name update never discards its Spotify ID."""
        name = name.strip()
        if not name:
            raise ValueError("target_playlist_name must not be blank.")
        values = [("target_playlist_name", name)]
        if playlist_id is not None:
            values.append(("target_playlist_id", playlist_id))
        with self._connection() as conn:
            self._ensure_schema(conn)
            conn.executemany(
                "INSERT INTO application_setting (setting_name, setting_value) VALUES (?, ?) "
                "ON CONFLICT(setting_name) DO UPDATE SET setting_value = excluded.setting_value",
                values,
            )

    def get_scheduler_state(self) -> SchedulerState:
        """Load scheduler attempts without considering manual job status."""
        with self._connection() as conn:
            self._ensure_schema(conn)
            rows = dict(conn.execute(
                "SELECT state_name, state_value FROM application_scheduler_state"
            ))
        return SchedulerState(
            last_history_attempt_at=rows.get("last_history_attempt_at"),
            last_today_attempt_date=rows.get("last_today_attempt_date"),
        )

    def record_scheduler_attempts(
        self,
        *,
        history_attempt_at: datetime | None = None,
        today_attempt_date: str | None = None,
    ) -> None:
        """Persist scheduler attempts before their finite jobs are invoked."""
        values = []
        if history_attempt_at is not None:
            values.append(("last_history_attempt_at", _serialize_datetime(history_attempt_at)))
        if today_attempt_date is not None:
            values.append(("last_today_attempt_date", today_attempt_date))
        if not values:
            return
        with self._connection() as conn:
            self._ensure_schema(conn)
            conn.executemany(
                """
                INSERT INTO application_scheduler_state (state_name, state_value)
                VALUES (?, ?)
                ON CONFLICT(state_name) DO UPDATE SET state_value = excluded.state_value
                """,
                values,
            )

    def get_spotify_retry_after_until(self) -> Optional[str]:
        """Return the shared Spotify cooldown deadline, if one is active."""
        with self._connection() as conn:
            self._ensure_schema(conn)
            row = conn.execute(
                "SELECT state_value FROM application_scheduler_state WHERE state_name = ?",
                ("spotify_retry_after_until",),
            ).fetchone()
        return row[0] if row else None

    def set_spotify_retry_after_until(self, value: datetime) -> None:
        """Persist a 429 deadline for every automatic pipeline caller."""
        with self._connection() as conn:
            self._ensure_schema(conn)
            conn.execute(
                "INSERT INTO application_scheduler_state (state_name, state_value) VALUES (?, ?) "
                "ON CONFLICT(state_name) DO UPDATE SET state_value = excluded.state_value",
                ("spotify_retry_after_until", _serialize_datetime(value)),
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

    def save_preview(self, fingerprint: str, created_at: datetime) -> None:
        """Record the engine preview that may safely be published.

        The tracks themselves remain in the existing report file.  Keeping only
        its deterministic input fingerprint here preserves the one production
        SQLite database while making preview validity explicit.
        """
        with self._connection() as conn:
            self._ensure_schema(conn)
            conn.execute("INSERT INTO application_preview (id, fingerprint, created_at) VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET fingerprint=excluded.fingerprint, created_at=excluded.created_at", (fingerprint, _serialize_datetime(created_at)))

    def get_preview(self) -> PreviewState | None:
        with self._connection() as conn:
            self._ensure_schema(conn)
            row = conn.execute("SELECT fingerprint, created_at FROM application_preview WHERE id = 1").fetchone()
        return PreviewState(*row) if row else None

    def clear_preview(self) -> None:
        with self._connection() as conn:
            self._ensure_schema(conn)
            conn.execute("DELETE FROM application_preview WHERE id = 1")

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
        conn.execute("CREATE TABLE IF NOT EXISTS application_preview (id INTEGER PRIMARY KEY CHECK (id = 1), fingerprint TEXT NOT NULL, created_at TEXT NOT NULL)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS application_scheduler_state (
                state_name TEXT PRIMARY KEY,
                state_value TEXT NOT NULL
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


def _deserialize_bool(value) -> bool | object:
    if value in (0, "0"):
        return False
    if value in (1, "1"):
        return True
    return value
