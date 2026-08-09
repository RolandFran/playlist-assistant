# Maintenance and diagnostic tools

Run all commands from the project root. These helper scripts are not part of the production application.

## Diagnostics

- `python tools/diagnostics/analyze.py` writes a history and candidate analysis to `reports/analyze_output.txt`.
- `python tools/diagnostics/stats.py` prints candidate and listening-history statistics.
- `python tools/diagnostics/check_track.py <Spotify-track-URL-or-ID>` inspects a track in the local source data, history, and current Today selection.
- `python tools/diagnostics/inspect_db_schema.py` prints the local SQLite schema.
- `python tools/diagnostics/recently_played_diag.py` checks the Recently Played API response through the application client.
- `python tools/diagnostics/spotify-recently-played-raw-diag.py` inspects raw Recently Played API pagination behavior.

## Maintenance

- `python tools/maintenance/migrate_db_names.py` runs the legacy one-time database table-name migration against `spotify_history.db`. It is retained only for old installations; current installations use `playlist_assistant.db` and do not need it.

## Verification

- `python tools/verification/verify_today_playlist.py` compares `reports/today_tracks.json` with the Spotify `Today` playlist.

The Spotify-based diagnostics and verification command require the normal local Spotify configuration in `.env`. The database-based commands require the local `playlist_assistant.db` data file.
