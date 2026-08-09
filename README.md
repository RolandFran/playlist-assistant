# Playlist Assistant

Playlist Assistant automatically creates a dynamic `Today` playlist from selected Spotify source playlists.

Sources are identified by the `#today-source` marker in their Spotify playlist description. The selection combines playback rarity, time since the last listen, and artist spacing.

## Current status

The current implementation runs locally as a Python application. The target platform is a Home Assistant app with its own interface for configuration, status, manual actions, and the generated playlist.

Currently included:

- Spotify Recently Played collector
- Extended Streaming History import for setup and recovery
- incremental source sync using `snapshot_id`
- SQLite database: `playlist_assistant.db`
- URI-first matching against listening history
- rare, long, and combined scoring
- artist minimum gap for the Today selection
- stale-result protection before publishing
- private publishing of the `Today` target playlist
- central CLI entry point: `run.py`

## Prerequisites

- Python 3
- Spotify Developer access / OAuth configuration
- Project Python dependencies

Local secrets belong in `.env` and are not versioned.

## Quick start

The main individual jobs:

```powershell
python run.py history
python run.py sources
python run.py score
python run.py publish
```

Scoring values can be provided explicitly for each run. Values that are not supplied retain their defaults:

```powershell
python run.py score --today-size 100 --rare-weight 70 --artist-gap 5
```

The same options are available for `python run.py today` and are passed to the scoring step.

Complete Today pipeline:

```powershell
python run.py today
```

For a future host or another persistent installation location, pass a data
directory. The production database and all reports for that run are then kept
there, without writing runtime data back into the application directory:

```powershell
python run.py today --data-dir C:\playlist-assistant-data
```

Without `--data-dir`, the local CLI keeps the existing project-local
`playlist_assistant.db` and `reports/` layout. The same technical argument is
available on the individual `history`, `sources`, `score`, and `publish`
commands.

Spotify write access is deliberately not automatic. For an actual publish:

```powershell
python run.py today --write
```

## Extended Streaming History import

Spotify export files can be imported into the production history database for initial setup, recovery, or reinstall scenarios:

```powershell
python history_import.py import\Streaming_History_Audio_2025.json
```

Its explicit database path remains available for setup or recovery:

```powershell
python history_import.py import\Streaming_History_Audio_2025.json --db C:\playlist-assistant-data\playlist_assistant.db
```

The importer accepts one or more JSON export files, validates them, and writes the whole batch transactionally. Re-importing the same export is safe: existing plays are skipped. The input files remain local and unversioned under `import/`; the importer itself is tracked production code and can later be reused by the Home Assistant app.

## Default values

```text
Today size:        200
Rare weight:        50
Long weight:        50
Artist minimum gap: 10
History polling:    90 minutes
Today scheduling:   enabled at local 04:00
```

Only the rare weight is configurable. The long weight is always calculated as its complement, so they add up to 100.

## Scheduling policy

The engine includes a persistent, Home-Assistant-independent scheduler policy for a future host to invoke. It is not a background daemon or service. History is due every configured interval (90 minutes by default); Today is enabled by default and due once per day at local `04:00`. The Today time uses strict 24-hour `HH:MM` validation.

Scheduled runs persist their own attempt state. After a restart, an overdue History run or missed Today slot is caught up once. Failed scheduled History runs wait for the next configured interval; failed Today runs wait for the next daily slot. A scheduled Today run uses the normal pipeline and writes to Spotify. This does not change the manual CLI: `python run.py today` remains a dry run and `python run.py today --write` remains an explicit manual publish.

## Data flow

```text
collector.py
    ↓
sync.py
    ↓
scoring.py
    ↓
publish.py
```

For `today`, `run.py` executes these steps in the order History → Sources → Scoring → Publish.

## Important files

- `run.py` – central CLI entry point
- `client.py` – central Spotify/Spotipy boundary
- `collector.py` – Recently Played sync
- `history_import.py` – Extended Streaming History import
- `sync.py` – source and playlist synchronization
- `scoring.py` – matching, scoring, and Today selection
- `publish.py` – freshness check and Spotify publishing
- `db_state.py` – state fingerprint for stale-result protection
- `application_paths.py` – production database and report path contract
- `scheduler.py` – persistent, explicitly invoked scheduling policy
- `PROJECT.md` – current authoritative project state
- `docs/docs-design-notes.md` – Architecture Decision Log

## Local, unversioned data

The repository does not include, among other things:

- `.env`
- Spotify OAuth tokens and cache files
- `playlist_assistant.db`
- `reports/`
- `import/`
- local backups and Python caches

## Documentation

Two documents serve different roles for development and architecture:

- [`PROJECT.md`](PROJECT.md) describes the current authoritative target and project state.
- [`docs/docs-design-notes.md`](docs/docs-design-notes.md) records architectural decisions and their evolution.

If an older ADR conflicts with `PROJECT.md`, the current state documented in `PROJECT.md` takes precedence.

## Development workflow

`main` is the stable, approved state. Changes are made in separate branches and reviewed through pull requests before merging into `main`.

After an approved merge, update the local checkout with:

```powershell
git pull
```

## Home Assistant

The Home Assistant app is the target architecture but is not yet fully implemented. Planned features include:

- configurable Today size
- rare/long weighting
- artist minimum gap
- history sync interval
- Spotify/degraded status
- manual actions
- tabular Today view with filtering and sorting

Further authoritative details are in [`PROJECT.md`](PROJECT.md).
