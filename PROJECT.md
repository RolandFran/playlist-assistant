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

Diagnostic and analysis tools are located in `tools/`, notably `tools/stats.py` and `tools/analyze.py`.

Importing Spotify Extended Streaming History is a local setup/import operation and intentionally lives outside the Git repository under `import/`.

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

The **user/configuration scale for weights is 0 to 100**.

For mathematical calculation, values may be normalized internally to factors from 0.0 to 1.0. This internal representation is not a user value.

Rare and Long should total 100. This also permits the extremes `100 / 0` (Rare only) and `0 / 100` (Long only). The later HA app implementation will decide how the UI couples the two values.

## Artist spacing

Default: `artist_min_gap = 10`

During selection, the same normalized artist should ideally not recur within the previous 10 selected positions.

Artist spacing does not change the score; it changes the ordering or selection.

If the configured spacing cannot be maintained with the remaining candidate pool, it may exceptionally be relaxed so the configured target size can be reached.

## Current local defaults

The intended user values are:

```text
TODAY_SIZE = 200
RARE_WEIGHT = 50
LONG_WEIGHT = 50
ARTIST_MIN_GAP = 10
```

The current code still holds the weight factors as `0.50 / 0.50` in `scoring.py`. This is transitional and will be replaced by a central configuration layer.

## History synchronization

`collector.py` runs one synchronization pass at a time.

The later Home Assistant app is currently intended to provide:

- automatic history polling every **90 minutes** by default
- preliminary configurable range: 15–180 minutes
- an additional history sync immediately before Today generation
- a manual history sync for diagnostics, testing, and setup

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
- rare weight
- long weight
- artist minimum gap
- history sync interval
- later scheduling/playlist options

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
- `collector.py` – one Recently Played synchronization pass
- `sync.py` – source playlist and candidate synchronization
- `scoring.py` – matching, scoring, and Today selection
- `publish.py` – freshness check and Spotify publishing
- `run.py` – central CLI entry point / Today pipeline
- `db_state.py` – database input state and fingerprint for stale-result protection
- `tools/` – diagnostic, analysis, and migration tools
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
- exact Today-generation scheduling logic
- exact HA Ingress/dashboard structure
- developer diagnostic view and status sensors
- final Spotify client file structure (`client.py` versus `spotify/` package)
- automated tests and mocking strategy
- technical delivery of app configuration values to the Python engine

## Repository change workflow

- Planning, architecture, and review happen primarily in the normal ChatGPT chat.
- Codex/Work is used selectively for clearly scoped repository and implementation work.
- Git is the authoritative technical reference between chat and Work.
- Larger changes should be made on a dedicated branch and reviewed through a pull request.
- Hermes is not currently a necessary intermediate step for this project and should not consume additional Work/Codex capacity without a concrete benefit.

## Repository language convention

Code, comments, docstrings, the README, PROJECT documentation, ADRs, issues, pull request titles, and pull request descriptions are written in English going forward. Runtime and terminal output are outside this convention until explicitly changed.
