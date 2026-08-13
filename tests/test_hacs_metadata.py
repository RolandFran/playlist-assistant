import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "playlist_assistant"


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def test_hacs_uses_standard_integration_layout():
    assert _read_json(ROOT / "hacs.json") == {"name": "Playlist Assistant"}

    integrations = [path for path in (ROOT / "custom_components").iterdir() if path.is_dir()]
    assert integrations == [INTEGRATION]


def test_hacs_brand_icon_is_present():
    icon = ROOT / "brand" / "icon.png"

    assert icon.is_file()
    assert icon.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_home_assistant_manifest_has_hacs_metadata():
    manifest = _read_json(INTEGRATION / "manifest.json")

    assert manifest["domain"] == "playlist_assistant"
    assert manifest["name"] == "Playlist Assistant"
    assert manifest["version"] == "0.3.6"
    assert manifest["iot_class"] == "cloud_polling"
    assert manifest["documentation"] == "https://github.com/RolandFran/playlist-assistant"
    assert manifest["issue_tracker"] == "https://github.com/RolandFran/playlist-assistant/issues"
    assert manifest["codeowners"] == ["@RolandFran"]


def test_registered_services_are_documented():
    services = (INTEGRATION / "services.yaml").read_text(encoding="utf-8")

    for service in ("sync", "preview", "publish", "run"):
        assert f"{service}:" in services
