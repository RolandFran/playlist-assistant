# Future Feature Backlog

Future features listed here are exploratory ideas. They are not part of the
current beta scope and should only be implemented after the existing core
functionality is stable.

This is an idea pool, not a roadmap, release commitment, priority list, or
implementation instruction. Unless explicitly recorded otherwise, every item
below has **Status: Idea**. The compact architectural direction remains in the
project's existing design documentation; this file deliberately collects the
more detailed product possibilities without changing that direction.

## Discover, selection, and control

- Play a generated selection directly, or save/publish it as a Spotify
  playlist; Play and Save remain separate outputs.
- Support multiple selections/profiles, one-off and scheduled execution, and
  multiple target playlists.
- Make selection parameters configurable.
- Add track pins, next-run pins, and permanent or recurring pins.
- Exclude individual source tracks explicitly.
- Add track and artist cooldowns, never-played priority, and source weights.

## Genres, smart grouping, and mood

- Choose genres during creation, exclude genres, and balance genres within a
  selection.
- Compare genre distribution between the source pool and generated selection.
- Add smart groups and mood groups, for example Quiet, Upbeat, Rock &
  Alternative, Jazz, and Classical.
- Group existing music automatically. If Spotify metadata proves insufficient,
  evaluate additional metadata providers later; no such integration is part of
  the current scope.

## Repair and lost tracks

- Detect unavailable or greyed-out Spotify tracks and maintain a separate
  Lost Tracks table.
- Detect Spotify relinking; search alternative Spotify IDs for the same
  recording using ISRC, album/re-release/remaster candidates, and optionally
  intentional cover versions.
- Allow a manual replacement ID, show uncertain candidates, and let users
  preview a replacement before adoption.
- Offer Replace, Ignore, and Search actions while keeping original and new
  track IDs distinct and preserving song history where possible.
- Never make uncertain automatic replacement decisions without user approval.

## Protect and playlist backup

Playlist backups remain clearly separate from Home Assistant app backups.

- Save Spotify playlist snapshots, including order, track ID/URI, title,
  artist, album, ISRC, and position.
- Provide manual backups and automatic snapshots, particularly before repair,
  restore, or other write operations.
- Restore a playlist through an initial preview/diff; first save the current
  state automatically.
- Support export/download and retention rules for backups.

## Insights and statistics

Statistics should help verify correct operation and reveal useful tuning, not
only decorate the interface.

- Show plays over time, top tracks/artists, unique tracks/artists by period,
  library/source coverage, forgotten tracks, and long-unplayed tracks.
- Measure rediscovery, including tracks played again after 30, 90, 180, and
  365 days.
- Compare genre and source-pool/selection distributions; identify artist or
  genre dominance and overall listening diversity.
- Track selection quality over time, diagnose whether scoring or selection
  rules need adjustment, and present graphs and visual trends.

## Data quality and history integrity

This concerns only possible **collection gaps** in live-history capture, never
ordinary periods in which no music was played. For example, a prior latest
known play at 10:00 followed by a poll returning the API maximum of 50 tracks
whose oldest result is 10:35 suggests a possible gap because the returned data
does not overlap the known history.

- Audit history polling, identify and show open collection gaps, and expose a
  History Health view.
- Support `open`, `accepted`, and `resolved` gap states.
- Let users consciously accept/ignore a gap; accepted gaps must not reappear
  as new failures.
- Re-check gaps after imports or subsequently added data.
- Do not interpret normal silent time as an error.

## Track identity and provenance

Future extensions should distinguish Spotify Track ID, Recording Identity, and
Playlist Entry. A selected track should later be explainable through provenance
such as source, score, rare and long-not-played components, selection reason,
genre/group, pin, and replacement information.

## Multiple accounts and capabilities

- Multiple Spotify accounts may be considered later.
- Some features may depend on Spotify Premium, granted OAuth scopes, or
  available metadata.
- Future UI can show the capabilities that are currently available.

No multi-account or feature-flag infrastructure is implied by these ideas.
