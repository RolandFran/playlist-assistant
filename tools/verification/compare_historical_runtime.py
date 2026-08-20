"""Verify the production HA runtime is a literal normalized Historical Test restore."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SOURCE_COMMIT = "672341dc5eb947db26fdb3243a41ae1356700318"
MAPPINGS = (
    (
        "historical_test/custom_components/playlist_assistant_historical_test",
        "custom_components/playlist_assistant",
        frozenset(),
    ),
    (
        "historical_test/playlist_assistant_historical_test",
        "ha_app",
        frozenset({"Dockerfile", "README.md"}),
    ),
)
TEXT_SUFFIXES = frozenset({".css", ".html", ".js", ".json", ".py", ".sh", ".yaml"})
REPLACEMENTS = (
    (b"playlist_assistant_historical_test", b"playlist_assistant"),
    (b"Playlist Assistant Historical Test", b"Playlist Assistant"),
    (b"8108", b"8098"),
    (b"8109", b"8099"),
    (b"playlist_assistant_historical_test.db", b"playlist_assistant.db"),
    (b'"0.3.6-beta.1"', b'"0.3.6-beta.13"'),
    (b'"0.1.27"', b'"0.1.37"'),
)


def git(*args: str) -> bytes:
    return subprocess.check_output(("git", *args))


def source_files(directory: str) -> list[str]:
    listing = git("ls-tree", "-r", "--name-only", SOURCE_COMMIT, "--", directory)
    return listing.decode().splitlines()


def normalized_source(path: str) -> bytes:
    content = git("show", f"{SOURCE_COMMIT}:{path}")
    if Path(path).suffix in TEXT_SUFFIXES:
        for before, after in REPLACEMENTS:
            content = content.replace(before, after)
    return content


def normalized_production(path: Path) -> bytes:
    content = path.read_bytes()
    # The prebuilt GHCR image reference is delivery metadata, not runtime code.
    if path.parent.name == "ha_app" and path.name == "config.yaml":
        content = b"\n".join(
            line for line in content.splitlines() if not line.startswith(b"image:")
        ) + b"\n"
    return content


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    mismatches: list[str] = []
    checked: list[tuple[str, str]] = []
    for source_root, production_root, exclusions in MAPPINGS:
        for source_path in source_files(source_root):
            relative = source_path.removeprefix(source_root + "/")
            if relative in exclusions:
                continue
            production_path = root / production_root / relative
            checked.append((source_path, production_path.relative_to(root).as_posix()))
            if not production_path.is_file():
                mismatches.append(f"missing: {production_path.relative_to(root)}")
                continue
            if normalized_source(source_path) != normalized_production(production_path):
                mismatches.append(
                    f"content differs: {source_path} -> {production_path.relative_to(root)}"
                )

    print(f"Historical source: {SOURCE_COMMIT}")
    print(f"Runtime files checked: {len(checked)}")
    for source_path, production_path in checked:
        print(f"MAP {source_path} -> {production_path}")
    if mismatches:
        print("Parity result: FAIL")
        print("\n".join(mismatches))
        return 1
    print("Parity result: PASS (all normalized runtime files are content-identical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
