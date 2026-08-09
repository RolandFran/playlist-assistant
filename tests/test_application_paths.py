import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from application_paths import APPLICATION_DIR, ApplicationPaths
from application_storage import ApplicationStorage
from run import run_script


class ApplicationPathsTests(unittest.TestCase):
    def test_default_paths_preserve_project_local_cli_layout(self):
        paths = ApplicationPaths.default()

        self.assertEqual(paths.data_dir, APPLICATION_DIR)
        self.assertEqual(paths.database_path, APPLICATION_DIR / "playlist_assistant.db")
        self.assertEqual(paths.reports_dir, APPLICATION_DIR / "reports")
        self.assertEqual(paths.backups_dir, APPLICATION_DIR / "backups")
        self.assertEqual(
            paths.today_tracks_path,
            APPLICATION_DIR / "reports" / "today_tracks.json",
        )

    @patch("run.subprocess.run")
    def test_default_cli_dispatch_keeps_existing_project_local_behavior(self, run):
        run.return_value.returncode = 0

        run_script("scoring.py")

        command = run.call_args.args[0]
        self.assertNotIn("--data-dir", command)

    def test_supplied_data_directory_owns_database_and_reports(self):
        code_database = APPLICATION_DIR / "playlist_assistant.db"
        code_report = APPLICATION_DIR / "reports" / "today_tracks.json"
        before = {
            path: path.read_bytes() if path.exists() else None
            for path in (code_database, code_report)
        }

        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory) / "persistent-data"
            paths = ApplicationPaths.from_data_dir(data_dir)
            paths.ensure_runtime_directories()

            ApplicationStorage(paths.database_path).load_runtime_config()
            paths.today_tracks_path.write_text("{}", encoding="utf-8")

            self.assertTrue(paths.database_path.is_file())
            self.assertTrue(paths.today_tracks_path.is_file())
            self.assertTrue(paths.database_path.is_relative_to(data_dir))
            self.assertTrue(paths.today_tracks_path.is_relative_to(data_dir))
            self.assertTrue(paths.backups_dir.is_relative_to(data_dir))

        after = {
            path: path.read_bytes() if path.exists() else None
            for path in before
        }
        self.assertEqual(after, before)

    @patch("run.subprocess.run")
    def test_cli_dispatch_forwards_supplied_data_directory(self, run):
        run.return_value.returncode = 0

        paths = ApplicationPaths.from_data_dir("host-persistent-data")
        run_script("scoring.py", paths=paths)

        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["--data-dir", "host-persistent-data"])
