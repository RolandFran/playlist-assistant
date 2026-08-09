# Playlist Assistant – Design Notes / Architecture Decision Log

Status: ongoing planning phase
Purpose: Record decisions concisely and preserve the rationale for architectural decisions.

`PROJECT.md` describes the current authoritative project state. This decision log documents decisions and may therefore include historical or later-superseded ADRs.

## ADR-001 – Centralize Spotify access behind a client layer
**Status:** accepted

- Spotipy remains the Spotify library for now.
- Spotipy is not used directly from `sync.py`, `collector.py`, `publish.py`, or other domain modules.
- All Spotify access goes through a central client layer (`client.py`, or possibly a `spotify/` package later).
- The client layer encapsulates authentication/token use, API limits and batch sizes, pagination, request counting, error classification, rate-limit/quota handling, and structured logging.
- Replacing Spotipy with direct HTTP calls should be possible without rebuilding the domain modules.
- A Spotipy replacement is considered only for a concrete technical reason.

## ADR-002 – Spotify API limits are internal implementation details
**Status:** accepted

- API limits and batch sizes are maintained centrally in code.
- They are not stored as normal user configuration.
- A future developer/diagnostic section may display current values read-only.
- Spotify changes should be correctable through an app update without old user values overriding a fix.
- Relevant values are checked against Spotify documentation before implementation.

## ADR-003 – Centralize pagination
**Status:** accepted

- Domain modules request complete logical data sets and do not know API pagination.
- For example, `sync.py` requests a source's tracks; the client layer decides how many pages are required.
- Pagination ends based on the API response (`next`, cursor, checkpoint, and so on).
- Spotify-specific page sizes must not be distributed across modules.

## ADR-004 – Keep source sync incremental
**Status:** accepted

- Source playlists are identified by `#today-source`.
- Unchanged sources are not fully reloaded.
- `snapshot_id` detects changes.
- New or genuinely changed sources are loaded.
- Removing `#today-source` cleanly removes the source from local data.
- SQLite changes only after the Spotify data required for the relevant consistent sync is loaded successfully.

## ADR-005 – Collect history on demand
**Status:** superseded by ADR-017

- Original decision: no permanent 30/60-minute collector by default.
- Recently Played should be updated immediately before Today generation.
- A manual history sync was also planned for diagnostics, testing, and setup.
- Pagination ends when the known history checkpoint is reached or the time gap is closed.
- ADR-017 adds an automatic 90-minute default and supersedes the first point of this ADR.

## ADR-006 – Distinguish rate limits from development quota
**Status:** accepted

- HTTP 429 is handled centrally.
- `QUOTA_EXCEEDED` is distinguished from a normal short-term rate limit.
- `Retry-After` is evaluated and respected.
- Small, reasonable wait times may be retried automatically in a controlled manner.
- Very long waits must not block a process for hours.
- A long lockout ends the current Spotify job in a controlled manner.
- The app itself remains available.
- No inconsistent partial database changes.

## ADR-007 – Degraded mode must be visible in the UI
**Status:** accepted

When Spotify is temporarily unavailable:

- local database evaluation remains usable,
- existing scores and playlist data remain visible,
- Spotify-dependent actions are disabled or greyed out,
- the reason for the lockout is shown,
- the earliest possible next attempt is shown when known, and
- the log contains technical details.

Example status values:

- `Spotify: OK`
- `Spotify: Rate limited`
- `Spotify: Quota erschöpft`
- `Spotify: verfügbar ab …`

The last two values are planned runtime UI strings and intentionally remain unchanged.

## ADR-008 – Logging and request counting
**Status:** accepted

- Structured logs go to stdout/stderr and should later appear in the native Home Assistant app **log** tab.
- Normal successful flows are logged compactly.
- Detailed individual-request logs can be enabled through developer/diagnostic options.
- Spotify requests are counted centrally.
- A job log should include at least job type, start/end, Spotify request count, number of read/written items, success/failure, reason and Retry-After for 429, and whether the database changed.

## ADR-009 – Home Assistant app as target platform
**Status:** accepted

Playlist Assistant is intended to run as a Home Assistant app.

Use Supervisor/app capabilities rather than rebuilding them: start/stop/restart, start at Home Assistant system startup, watchdog, automatic updates, sidebar entry/Ingress, native tabs for information, documentation, configuration, and logs, container resource display (CPU/RAM) where provided by Supervisor, and app/container hostname where provided.

This decision sets the target platform, not the internal HA interface. Whether additional entities, services, or a custom integration are needed remains a separate architecture decision.

## ADR-010 – Configuration page: user options versus developer diagnostics
**Status:** accepted

Normal user configuration:

- Today size
- Rare/Long weight
- artist minimum gap
- later scheduling/playlist options

Developer/diagnostic area:

- log level
- detailed Spotify request logging
- API diagnostics
- dry run
- internal Spotify limits, read-only

Not user options:

- Spotify page size
- Spotify write batch size
- internal retry constants unless there is a real user case

## ADR-011 – Add caching only for tangible benefit
**Status:** accepted

- Do not add an ETag/cache layer merely for theoretical optimization.
- Add it only when it demonstrably reduces requests or simplifies code.
- Existing mechanisms such as `snapshot_id` and the history checkpoint take precedence.

## ADR-012 – Documentation strategy
**Status:** accepted

- `PROJECT.md` is the project's current authoritative specification.
- This decision log records decisions and their evolution; older ADRs are marked as superseded when changed rather than silently overwritten.
- Continue this decision log during the planning phase.
- Later documentation: `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/spotify-api.md`, `docs/database.md`, and `docs/development.md`.
- `AGENTS.md` remains short and authoritative; detailed knowledge belongs in `docs/`.

## ADR-013 – Division of work: Chat / Hermes / Codex
**Status:** accepted, refined

- Planning, architecture, decisions, and review happen primarily in the standard ChatGPT chat.
- Codex/Work is used selectively for clearly scoped repository and implementation work.
- GitHub is the handoff point between chat, Work/Codex, and the local project state.
- Changes are made on a dedicated branch and reviewed through a pull request before merge.
- Hermes is not currently a standard orchestrator for this project.
- Hermes should not consume Codex/Work capacity for project administration, Kanban maintenance, or unnecessary worker orchestration.
- If Hermes is used later, a worker plan with task, model, and reasoning level must be presented and approved before creating a worker.

## Open items

The following items are not final and will be completed later:

- exact retry thresholds for short versus long 429 lockouts
- persistent app status for Spotify lockouts / retry time
- exact Today-generation scheduling logic
- exact HA Ingress/dashboard structure
- developer diagnostic view and status sensors
- final file structure (`client.py` versus `spotify/` package)
- automated tests and mocking strategy

## ADR-014 – Initial Spotify client refactor
**Status:** implemented as a tested state

- `client.py` is now the only Spotify/Spotipy boundary for `collector.py`, `sync.py`, and `publish.py`.
- Spotipy internal status retries are disabled (`retries=0`, `status_retries=0`).
- Short 429 lockouts are handled in a controlled manner by the client layer.
- Long 429 lockouts result in a controlled error instead of hours of sleep.
- `QUOTA_EXCEEDED` has its own exception.
- 5xx errors receive a few short retries.
- Request counting is centralized.
- Playlist and Recently Played pagination are centralized in `client.py`.
- `publish.py` no longer uses a separate `requests` dependency.
- All three jobs log structured start/end/error events.
- A live test against Spotify remains outstanding.

## ADR-015 – Normalize Spotify playlist metadata centrally
**Status:** implemented

- Spotify/Spotipy field names such as `items` versus the older `tracks` are handled only in `client.py`.
- `client.py` exposes the internal `item_total` field to domain modules.
- `sync.py` no longer knows Spotify-specific field names.
- API/Spotipy field changes therefore do not directly cause unnecessary full syncs.

## ADR-016 – Close Recently Played gaps backwards
**Status:** implemented as a tested state

- An `after=<checkpoint>` request returns at most 50 plays and is insufficient for larger gaps.
- After the first page, paginate backwards as needed with `before=<oldest timestamp on page>`.
- Never send `after` and `before` together.
- Only accept plays after the requested checkpoint.
- Existing plays remain unchanged through the database primary key/`INSERT OR IGNORE`.
- `collector.py --recover-after <ISO timestamp>` permits a targeted backfill of a gap that has already formed.
- A recovery run must never move the stored `last_played_at` checkpoint backwards.

## ADR-017 – History collector: 90-minute default and gap detection
**Status:** accepted / foundation implemented

- The future scheduling target defaults to **90 minutes** for history polling.
- The interval is later app-layer configuration; this decision does not create a daemon or hard-code a daily Today execution time.
- An additional sync immediately before Today generation remains planned.
- A manual history sync remains planned.
- If Spotify returns exactly a full Recently Played page and the oldest returned play is still after the stored checkpoint, the collector sets `gap_possible=true`.
- A possible history gap is logged and should later be visible in the UI.
- Isolated small gaps are tolerable; systematic or large gaps should be detectable.
- `collector.py` continues to run one synchronization pass; scheduler-ready runtime orchestration is defined in ADR-024.

## ADR-018 – Stale-result protection for Today
**Status:** implemented

- `scoring.py` stores a fingerprint of database input state in `today_tracks.json`.
- The fingerprint includes active sources, source snapshots, playlist/history counters, and history checkpoints.
- `publish.py` recalculates the current fingerprint before every dry run/write.
- When fingerprints differ, publishing is aborted before every Spotify write.
- This prevents a `today_tracks.json` made stale by a source sync or history update from being published accidentally.
- The check is state-based, not timestamp-based.

## ADR-019 – Track matching: Spotify URI first
**Status:** implemented and verified with a real case

- Historical plays are assigned to source tracks primarily through exact `track_uri`.
- Only when that URI has no match does matching fall back to normalized title and artist.
- Spotify metadata can differ between the Playlist API and Extended Streaming History even when the same track ID is intended.
- Verified case: `Amour, Mon Cher Amour`
  - Playlist artist: `Hot Club De Norvege, Jon Larsen, Jimmy Rosenberg`
  - History artist: `Hot Club De Norvege`
  - Spotify URI is identical
  - 26 history plays were correctly recognized through URI.
- Internal match values remain machine-readable (`uri`, `title_artist`, `none`); reports use readable labels (`URI`, `Titel+Interpret`, `kein Match`). The German report labels are runtime output and remain unchanged.

## ADR-020 – Plain-language diagnostic terms
**Status:** implemented

- `Max. Tage seit Play` is emitted as `Längste Hörpause`.
- `Max. Play-Count` is emitted as `Höchste Wiedergabezahl`.
- Technical internal field names remain unchanged; only user/console output is worded more clearly.

## ADR-021 – User weights use a 0–100 scale
**Status:** accepted

- `rare_weight` is the only user-configurable weight and is represented as an integer on a 0–100 scale in configuration and UI.
- `long_weight` is always derived as `100 - rare_weight`; the default is Rare `50` / derived Long `50`.
- The complete Rare range constructs the corresponding Long range: `0 / 100` through `100 / 0`.
- Rare and Long therefore always total 100 without two independently supplied user weights.
- The scoring formula may normalize these internally to factors from 0 to 1.
- Internal normalization is an implementation detail and must not force users to configure values such as `0.50` again.

## ADR-022 – GitHub branch and PR workflow
**Status:** accepted

- `main` is the stable, approved project state.
- Changes are always made on a separate branch.
- A pull request is created before merging into `main`.
- The pull request is the approval point: changed files and the diff are reviewed before merging.
- After a merge, the local working directory synchronizes the approved state with `git pull`.
- This process applies to changes from the standard chat and future Work/Codex implementations.

## ADR-023 – Repository language convention
**Status:** accepted

- Code, comments, docstrings, README, PROJECT documentation, ADRs, issues, pull request titles, and pull request descriptions use English.
- Runtime and terminal output are excluded from this convention until changed by a separate decision.

## ADR-024 – Scheduler-ready runtime orchestration
**Status:** implemented

- `runtime.py` provides an in-process boundary for explicit `history` and `today` jobs.
- The `today` job preserves the order History → Sources → Scoring → Publish.
- Every job returns success/failure, start/end timestamps, duration, and the failed step when applicable.
- Same-job overlap is rejected within one process; no distributed lock is introduced.
- The default future history cadence is exposed as 90 minutes, but no daemon, OS scheduler, Home Assistant dependency, or player-state check is added.
- Spotify API and rate-limit handling remain in the existing client and domain layers.
