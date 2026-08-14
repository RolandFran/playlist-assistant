# Future Ideas Backlog

This directory is the prioritized pool of work intentionally deferred beyond the current stable scope.

**Current development priority: Beta stabilization.** No item below should interrupt that work unless it becomes necessary to remove a concrete blocker or architectural dead end.

Priority describes the intended order of evaluation after Beta stability, not a release commitment.

## P1 — Next candidates after Beta stabilization

1. [Direct playback and Play/Save outputs](playback/direct-playback.md)
2. [Daily selection model](playback/daily-selection.md)
3. [Extended analytical track table](analysis/extended-track-table.md)
4. [Metadata provider enrichment](metadata/metadata-providers.md)

## P2 — Build on the P1 foundation

5. [Selection profiles and advanced controls](selection/profiles-and-controls.md)
6. [Genres, mood groups, and smart grouping](classification/genres-moods-smart-groups.md)
7. [Audio features and sonic analysis](metadata/audio-features.md)
8. [Insights and statistics](analysis/insights-and-statistics.md)

## P3 — Later product areas

9. [Lost-track repair and replacement](repair/lost-track-repair.md)
10. [Playlist backup and protection](protect/playlist-backup.md)
11. [History integrity and data quality](data-quality/history-integrity.md)
12. [Multiple accounts and capability handling](accounts/multiple-accounts.md)

## Backlog maintenance rule

Each durable future idea gets one canonical file in this tree. Further discussion updates that file instead of creating parallel notes. New ideas are added here with a priority. When an idea becomes implemented, its status is updated and the authoritative current behavior is reflected in `PROJECT.md` and, where appropriate, the ADR.

The previous `docs/future-features.md` is retained as a legacy summary/pointer during migration so existing references do not silently break.