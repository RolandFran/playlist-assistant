# Playlist Assistant – Authoritative Project State

## Purpose of this file

`PROJECT.md` describes the **current authoritative project state** and target architecture.

Historical decisions and their rationales are maintained separately in `docs/docs-design-notes.md` as an Architecture Decision Log (ADR). Older ADRs may be superseded and therefore do not automatically represent the current target state.

## Goal

Playlist Assistant creates a dynamic Spotify target playlist from defined source playlists.

Candidates come exclusively from Spotify playlists whose description contains the `#today-source` marker.

The Today selection is generated from a score. Its default size is 200 tracks and will later be configurable through the Home Assistant app.

The Spotify target playlist managed by Playlist Assistant, `Today`, is private.

## Target platform

Playlist Assistant is intended to run as a **Home Assistant app**.

The app should use Home Assistant/Supervisor capabilities, including:

- start / stop / restart
- start with the Home Assistant system
- watchdog
- app updates
- sidebar entry / Ingress
- native areas for information, documentation, configuration, and logs
- Supervisor resource information when available

The playlist engine remains logically separate from the existing Home Assistant system. Existing HA configurations, integrations, and Node-RED flows should not need to change for the core function.

## Versioning

The Custom Integration and Home Assistant add-on have independent SemVer versions; they are never artificially synchronized. For each component, PATCH is a bugfix without a feature, MINOR is a backward-compatible feature, and MAJOR is an incompatible change or stable development jump. The current OAuth proof therefore keeps the Custom Integration at `0.3.0` and the add-on at `0.1.10`.

## Central database

File: `playlist_assistant.db`

There is exactly one production SQLite database.

### Tables

- `source` – currently discovered Spotify source playlists with `#today-source`
- `playlist` – current tracks in those source playlists; a track can occur in multiple sources
- `history` – individual Spotify plays from Extended Streaming History and the running collector
- `sync_state` – technical collector checkpoints

## Current data flow

1. `collector.py` updates Spotify Recently Played and writes new plays to `history` and checkpoints to `sync_state`.
2. `sync.py` finds playlists with `#today-source` and incrementally updates `source` and `playlist`.
3. `scoring.py` evaluates `playlist` candidates against `history`, calculates scores, and generates the Today selection.
4. `publish.py` checks the freshness of the scoring result and publishes the selection to Spotify.
5. `run.py` is the central CLI entry point and can run the complete Today pipeline in a fixed order: History → Sources → Scoring → Publish.

Diagnostic and analysis tools are located in `tools/diagnostics/`, notably `tools/diagnostics/stats.py` and `tools/diagnostics/analyze.py`. See `tools/README.md` for the complete categorized tool reference.

`history_import.py` imports Spotify Extended Streaming History exports into the same `history` table for setup, recovery, and reinstall scenarios. It is tracked production code, independent of Home Assistant, and returns a structured result for future UI use. Raw export files remain outside Git under the local `import/` directory.

Imports validate supported music-play records, are idempotent through the existing history primary key, and write each requested file batch transactionally. A failed batch does not commit partial imported plays. The normal Recently Played collector then continues against this same database state.

## Spotify access

`client.py` is the central Spotify/Spotipy boundary for the domain modules.

The client layer encapsulates:

- authentication / token use
- API calls
- pagination
- Spotify batch sizes
- request counting
- error classification
- rate-limit / quota handling
- logging

Spotify-specific API limits are internal implementation details, not normal user configuration.

## Source sync

- Source playlists are identified by `#today-source`.
- `snapshot_id` is used to detect changes.
- Unchanged sources are not fully reloaded.
- New or genuinely changed sources are synchronized.
- Removing `#today-source` removes the source from the local data store.
- The database changes only after the Spotify data required for a consistent sync has been loaded successfully.

## Candidates and song identity

Candidates come exclusively from `playlist`.

A logical song candidate currently uses:

- normalized title
- normalized artist

Multiple playlist entries with the same normalized title and artist are treated as one logical candidate. A Spotify URI remains as a technical reference so that the selected track can be published later.

Normalization currently includes only:

- letter case
- surrounding whitespace

Live/remaster/acoustic suffixes are not removed.

## Matching against listening history

Historical plays are matched in this order:

1. **Primary:** exact Spotify `track_uri`
2. **Fallback:** normalized title + normalized artist

The URI match takes precedence because Spotify metadata can differ between the Playlist API and Extended Streaming History even when the same Spotify track ID is intended.

For playlist candidates, plays are considered only from `added_at` onward when `added_at` is available.

Internal match types:

- `uri`
- `title_artist`
- `none`

## Scoring

All visible scores use a **0 to 100** scale.

### Rare score

- logarithmic over `play_count`
- 0 plays → rare score 100
- the highest current play count is the upper comparison bound

### Long-not-played score

- listened tracks: logarithmic over days since the last relevant play
- 0-play tracks: neutral long score of 50
- for equally scored 0-play tracks, age since `added_at` is the tie-breaker; older entries are considered first
- never-played tracks therefore remain high priority, but do not automatically displace the entire Today selection

### Combined score

Default weighting:

- Rare: 50
- Long: 50

`rare_weight` is the only configurable weight and uses a **0 to 100** user/configuration scale. `long_weight` is always derived as `100 - rare_weight`.

For mathematical calculation, values may be normalized internally to factors from 0.0 to 1.0. This internal representation is not a user value.

The complete Rare range maps constructively to Long: `0` Rare produces `100` Long, and `100` Rare produces `0` Long. The two weights therefore always total 100 without an independently configurable Long input.

## Artist spacing

Default: `artist_gap = 10`

During selection, the same normalized artist should ideally not recur within the previous 10 selected positions.

Artist spacing does not change the score; it changes the ordering or selection.

If the configured spacing cannot be maintained with the remaining candidate pool, it may exceptionally be relaxed so the configured target size can be reached.

## Current local defaults

`RuntimeConfig` is the central configuration layer. Its defaults are:

```text
today_size = 200
rare_weight = 50
long_weight = 50 (derived)
artist_gap = 10
history_poll_minutes = 90
today_schedule_enabled = true
today_schedule_time = 04:00 (local time, 24-hour HH:MM)
```

Application settings are persisted in the existing `playlist_assistant.db` through `application_storage.py`. `long_weight` is derived as `100 - rare_weight`; it is not independently configurable or stored. `RuntimeConfig` also exposes the normalized factors used by the scoring formula.

## Persistent application paths

`ApplicationPaths` is the single engine-level contract for persistent runtime
data. It owns the production `playlist_assistant.db`, `reports/`, and future
backup output locations.

The local CLI defaults to the existing project-local layout: the database and
reports remain beside the application code. A future host can pass
`--data-dir DIRECTORY` to `run.py` or an individual production command; then
all production database and report output is written under that directory.
This is a technical host handoff, not a normal user setting. Supplying a data
directory never falls back to writes in the application-code directory.

Existing local databases, reports, imports, and backups are neither moved nor
automatically imported.

## History synchronization

`collector.py` runs one synchronization pass at a time.

`runtime.py` provides scheduler-ready orchestration for explicit `history` and `today` jobs. Each invocation records success or failure, start and end timestamps, duration, and the failed pipeline step when applicable. Completed results are persisted as serializable last-job status in the existing SQLite database, including error type/message and the last successful completion time. It rejects overlapping runs of the same job within one process.

`scheduler.py` provides a Home-Assistant-independent, explicitly invoked scheduler policy. It does not run a daemon, permanent process loop, or host service. Its persisted scheduler state is separate from manual job status, so only scheduled attempts affect cadence decisions. Default policy: History is due every 90 minutes; Today is enabled and due once per local day at 04:00. An overdue job is caught up once after restart. Failed scheduled History and Today attempts wait for their next normal interval or daily slot rather than retrying tightly. Scheduled Today calls the existing Today pipeline with `write=True`; manual CLI semantics remain unchanged.

The `ha_app/` package is the first host runtime foundation. Its small service
host invokes this existing policy once per minute and does not duplicate
scheduler or Spotify pipeline logic. It uses `--data-dir /data`, starts with
Home Assistant's `startup: application` behavior, supplies a watchdog-only
health endpoint, and remains running in a visible `not_connected` state until
an existing Spotify authorization cache is available. No browser authorization,
Ingress UI, Home Assistant configuration access, Node-RED dependency, or
second database is included in this foundation.

The configured target cadence for future scheduling is:

- history polling every **90 minutes** by default
- an additional history sync immediately before Today generation
- a manual history sync for diagnostics, testing, and setup

Today scheduling is persisted independently of Home Assistant: enabled by default at local 04:00, with time validated as 24-hour `HH:MM`.

A possible history gap should be detected and made visible in the UI later.

## Publishing and stale-result protection

`scoring.py` stores a fingerprint of the database input state used in `reports/today_tracks.json`.

`publish.py` recalculates the current fingerprint before a dry run or write.

If sources or history change since scoring, publishing is aborted. This prevents an outdated Today selection from being published accidentally.

The target playlist is created as private or set to private.

## Rate limits and degraded mode

Spotify errors are handled centrally by `client.py`.

In particular:

- HTTP 429 is handled in a controlled manner.
- `QUOTA_EXCEEDED` is distinguished from a normal short-term rate limit.
- `Retry-After` is evaluated.
- short, reasonable wait periods may be retried in a controlled manner.
- long lockouts must not block a process for hours.
- a long lockout ends the relevant Spotify job in a controlled manner.
- inconsistent partial database changes should be avoided.

The HA app is intended to show a visible degraded mode. Local database evaluation and existing results should remain usable while Spotify-dependent actions are disabled or shown as unavailable.

## Home Assistant configuration

Normal user configuration should include at least:

- Today size / `today_size`
- rare weight / `rare_weight` (Long is derived, not independently configured)
- artist minimum gap
- history sync interval
- Today scheduling enabled/time and later playlist options

The Python engine should obtain its runtime values from a central configuration layer.

Today this layer provides local defaults; later the Home Assistant app will provide configured values.

It is **not yet decided** whether individual values will technically be provided by HA entities, app configuration, an internal app API, or a combination.

## UI goal

The Home Assistant interface should later provide at least:

- understandable controls for relevant parameters
- Spotify/degraded status
- manual actions such as history sync and Today generation
- the generated Today playlist as a readable table
- filtering and sorting for the playlist table
- developer/diagnostic information separated from normal user options

## Reports

Current development/verification outputs:

- `reports/scoring_output.txt` – complete candidate list with score, Rare, Long, plays, and days
- `reports/today_output.txt` – currently selected Today tracks in the order produced by artist spacing
- `reports/today_tracks.json` – structured Today data for publishing and later processing

Plain-language diagnostic terms:

- `Höchste Wiedergabezahl`
- `Längste Hörpause`

The German labels above are runtime output and intentionally remain unchanged. Text reports are development/verification output; the Home Assistant interface is the long-term primary UI.

## File responsibilities

- `client.py` – central Spotify/Spotipy boundary
- `runtime.py` – scheduler-ready execution of explicit history and Today jobs
- `scheduler.py` – persistent, explicitly invoked scheduling policy
- `application_storage.py` – SQLite boundary for application settings, job status, and scheduler attempt state
- `application_paths.py` – persistent data-path contract for local and hosted execution
- `collector.py` – one Recently Played synchronization pass
- `history_import.py` – transactional Extended Streaming History import
- `sync.py` – source playlist and candidate synchronization
- `scoring.py` – matching, scoring, and Today selection
- `publish.py` – freshness check and Spotify publishing
- `run.py` – central CLI entry point / Today pipeline
- `db_state.py` – database input state and fingerprint for stale-result protection
- `tools/` – categorized diagnostic, maintenance, and verification tools; see `tools/README.md`
- `docs/docs-design-notes.md` – Architecture Decision Log / decision history

## Mandatory naming rules

Do not use:

- `spotify_history.db`
- `source_playlists`
- `playlist_tracks`
- `plays`
- `history.source`

Use instead:

- `playlist_assistant.db`
- `source`
- `playlist`
- `history`
- `history.data_source`

## Open architecture items

- exact retry thresholds for short versus long 429 lockouts
- persistent app status for Spotify lockouts / retry time
- exact HA Ingress/dashboard structure
- developer diagnostic view and status sensors
- final Spotify client file structure (`client.py` versus `spotify/` package)
- automated tests and mocking strategy
- technical delivery of app configuration values to the Python engine

## Repository change workflow

- Planning, architecture, and review happen primarily in the normal ChatGPT chat.
- Codex/Work is used selectively for clearly scoped repository and implementation work.
- Git is the authoritative technical reference between chat and Work.
- The mandatory development and release workflow is documented in `docs/development.md`.
- Hermes is not currently a necessary intermediate step for this project and should not consume additional Work/Codex capacity without a concrete benefit.

## Repository language convention

Code, comments, docstrings, the README, PROJECT documentation, ADRs, issues, pull request titles, and pull request descriptions are written in English going forward. Runtime and terminal output are outside this convention until explicitly changed.
