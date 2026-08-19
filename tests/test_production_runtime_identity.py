from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (
    ROOT / "custom_components" / "playlist_assistant",
    ROOT / "ha_app",
)
HISTORICAL_IDENTIFIERS = (
    "playlist_assistant_historical_test",
    "Playlist Assistant Historical Test",
    "historical_test",
)


def test_production_runtime_excludes_historical_test_identity():
    runtime_files = (
        path
        for root in RUNTIME_ROOTS
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".json", ".yaml", ".yml", ".js", ".css", ".html", ".sh"}
    )

    for path in runtime_files:
        content = path.read_text(encoding="utf-8")
        for identifier in HISTORICAL_IDENTIFIERS:
            assert identifier not in content, f"{identifier} remains in {path.relative_to(ROOT)}"


def test_production_addon_keeps_the_existing_database_name():
    paths = (ROOT / "ha_app" / "application_paths.py").read_text(encoding="utf-8")

    assert '"playlist_assistant.db"' in paths
    assert "playlist_assistant_historical_test.db" not in paths
