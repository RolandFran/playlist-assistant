import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from history_export import export_extended_history
from history_import import ensure_history_table, import_extended_history


class HistoryExportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "playlist_assistant.db"
        with closing(sqlite3.connect(self.database)) as conn:
            ensure_history_table(conn)
            conn.executemany(
                """INSERT INTO history (played_at, track_id, track_uri, track_name, artist_name, album_name, ms_played, skipped, reason_start, reason_end, offline) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    ("2026-08-03T23:59:59Z", "before", "spotify:track:before", "Before", "Artist", None, None, None, None, None, None),
                    ("2026-08-04T00:00:00Z", "boundary", "spotify:track:boundary", "Boundary", "Artist", "Album", 0, 1, "playbtn", "fwdbtn", 0),
                    ("2026-08-05T12:00:00+00:00", "after", "spotify:track:after", "After", "Artist", "Album", 1234, 0, "trackdone", "trackdone", 1),
                ],
            )
            conn.commit()

    def tearDown(self):
        self.directory.cleanup()

    def test_maps_history_to_stable_spotify_extended_history_records(self):
        records = export_extended_history(self.database)

        self.assertEqual([record["ts"] for record in records], ["2026-08-03T23:59:59Z", "2026-08-04T00:00:00Z", "2026-08-05T12:00:00+00:00"])
        self.assertEqual(records[1]["spotify_track_uri"], "spotify:track:boundary")
        self.assertEqual(records[1]["master_metadata_track_name"], "Boundary")
        self.assertTrue(records[1]["skipped"])
        self.assertFalse(records[1]["offline"])
        self.assertIsNone(records[0]["master_metadata_album_album_name"])
        self.assertIsNone(records[0]["skipped"])
        self.assertIsNone(records[0]["platform"])
        self.assertIsNone(records[0]["ip_addr"])
        self.assertNotIn("ip_addr_decrypted", records[0])
        self.assertNotIn("user_agent_decrypted", records[0])
        self.assertIsNone(records[0]["audiobook_title"])
        self.assertIsNone(records[0]["offline_timestamp"])

    def test_from_date_is_inclusive_at_utc_midnight(self):
        records = export_extended_history(self.database, from_date="2026-08-04")

        self.assertEqual([record["ts"] for record in records], ["2026-08-04T00:00:00Z", "2026-08-05T12:00:00+00:00"])

    def test_export_round_trips_through_existing_importer_and_overlaps_are_skipped(self):
        export = Path(self.directory.name) / "history-export.json"
        export.write_text(json.dumps(export_extended_history(self.database)), encoding="utf-8")
        restored = Path(self.directory.name) / "restored.db"

        first = import_extended_history([export], db_path=restored)
        second = import_extended_history([export], db_path=restored)

        self.assertTrue(first.success)
        self.assertEqual(first.plays_inserted, 3)
        self.assertTrue(second.success)
        self.assertEqual(second.plays_inserted, 0)
        self.assertEqual(second.duplicates_skipped, 3)

    def test_invalid_from_date_is_rejected_without_opening_or_creating_database(self):
        missing = Path(self.directory.name) / "missing.db"
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            export_extended_history(missing, from_date="04/08/2026")
        self.assertFalse(missing.exists())
