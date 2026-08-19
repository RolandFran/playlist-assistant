import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


HA_APP_DIR = Path(__file__).resolve().parents[1] / "ha_app"
PUBLISH_PATH = HA_APP_DIR / "publish.py"


def _load_publish_module():
    sys.path.insert(0, str(HA_APP_DIR))
    try:
        spec = importlib.util.spec_from_file_location("playlist_assistant_test_publish", PUBLISH_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


publish = _load_publish_module()


class PublishTargetMetadataTests(unittest.TestCase):
    def test_persisted_target_is_resolved_to_current_spotify_metadata(self):
        client = Mock()
        client.get_all_user_playlists.return_value = [
            {"id": "other", "name": "Other", "public": False},
            {"id": "target", "name": "Test", "public": False},
        ]

        result = publish.resolve_target_playlist(client, "Test", "target")

        self.assertEqual(result, {"id": "target", "name": "Test", "public": False})
        client.find_owned_playlist_by_name.assert_not_called()

    def test_persisted_private_target_omitted_from_listing_is_resolved_directly(self):
        client = Mock()
        client.get_all_user_playlists.return_value = [
            {"id": "other", "name": "Other", "public": False},
        ]
        client.get_playlist.return_value = {
            "id": "target",
            "name": "Test",
            "public": False,
        }

        target = publish.resolve_target_playlist(client, "Test", "target")
        changed = publish.prepare_publish_target(client, target, "Test")

        self.assertEqual(target, {"id": "target", "name": "Test", "public": False})
        self.assertTrue(changed)
        client.get_playlist.assert_called_once_with("target")
        client.prepare_private_playlist.assert_called_once_with("target", "Test")

    def test_matching_private_target_always_writes_the_proven_public_false_metadata(self):
        client = Mock()
        target = {"id": "target", "name": "Test", "public": False}

        changed = publish.prepare_publish_target(client, target, "Test")

        self.assertTrue(changed)
        client.prepare_private_playlist.assert_called_once_with("target", "Test")

    def test_public_target_still_enforces_private_visibility(self):
        client = Mock()
        target = {"id": "target", "name": "Test", "public": True}

        changed = publish.prepare_publish_target(client, target, "Test")

        self.assertTrue(changed)
        client.prepare_private_playlist.assert_called_once_with("target", "Test")

    def test_unknown_target_metadata_preserves_safe_details_write(self):
        client = Mock()
        target = {"id": "target"}

        changed = publish.prepare_publish_target(client, target, "Test")

        self.assertTrue(changed)
        client.prepare_private_playlist.assert_called_once_with("target", "Test")


if __name__ == "__main__":
    unittest.main()
