import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from history_import import import_extended_history


class HistoryImportTests(unittest.TestCase):
    def write_export(self, directory, name, records):
        path = Path(directory) / name
        path.write_text(json.dumps(records), encoding="utf-8")
        return path

    def valid_record(self, *, timestamp="2026-08-01T12:00:00Z"):
        return {
            "ts": timestamp,
            "spotify_track_uri": "spotify:track:track-123",
            "master_metadata_track_name": "A Track",
            "master_metadata_album_artist_name": "An Artist",
            "master_metadata_album_album_name": "An Album",
            "ms_played": 12345,
            "skipped": False,
            "offline": True,
            "reason_start": "playbtn",
            "reason_end": "trackdone",
        }

    def test_imports_supported_records_and_reports_invalid_ones(self):
        with tempfile.TemporaryDirectory() as directory:
            export = self.write_export(
                directory,
                "history.json",
                [self.valid_record(), {"ts": "not-a-music-play"}],
            )
            database = Path(directory) / "history.db"

            result = import_extended_history([export], db_path=database)

            self.assertTrue(result.success)
            self.assertEqual(result.files_processed, 1)
            self.assertEqual(result.records_read, 2)
            self.assertEqual(result.plays_inserted, 1)
            self.assertEqual(result.duplicates_skipped, 0)
            self.assertEqual(result.invalid_records, 1)

            with closing(sqlite3.connect(database)) as conn:
                row = conn.execute(
                    "SELECT track_id, data_source, skipped, offline FROM history"
                ).fetchone()

            self.assertEqual(row, ("track-123", "extended", 0, 1))

    def test_reimport_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            export = self.write_export(
                directory,
                "history.json",
                [self.valid_record()],
            )
            database = Path(directory) / "history.db"

            first = import_extended_history([export], db_path=database)
            second = import_extended_history([export], db_path=database)

            self.assertTrue(first.success)
            self.assertEqual(first.plays_inserted, 1)
            self.assertTrue(second.success)
            self.assertEqual(second.plays_inserted, 0)
            self.assertEqual(second.duplicates_skipped, 1)

    def test_malformed_file_rolls_back_the_entire_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            valid_export = self.write_export(
                directory,
                "valid.json",
                [self.valid_record()],
            )
            malformed_export = Path(directory) / "malformed.json"
            malformed_export.write_text("{not valid JSON", encoding="utf-8")
            database = Path(directory) / "history.db"

            result = import_extended_history(
                [valid_export, malformed_export],
                db_path=database,
            )

            self.assertFalse(result.success)
            self.assertIn("Expecting", result.error)
            with closing(sqlite3.connect(database)) as conn:
                table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'history'"
                ).fetchone()
                count = 0 if table is None else conn.execute(
                    "SELECT COUNT(*) FROM history"
                ).fetchone()[0]

            self.assertEqual(count, 0)

    def test_non_array_export_fails_without_creating_history_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            export = self.write_export(directory, "invalid.json", {"records": []})
            database = Path(directory) / "history.db"

            result = import_extended_history([export], db_path=database)

            self.assertFalse(result.success)
            self.assertIn("JSON array", result.error)
            with closing(sqlite3.connect(database)) as conn:
                table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'history'"
                ).fetchone()

            self.assertIsNone(table)
