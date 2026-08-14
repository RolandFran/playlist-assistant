# Extended Analytical Track Table

Status: Idea
Priority: P1
Area: UI / Analysis
Depends on: Beta stability

## Goal

Turn the existing track table into the primary analytical view for detailed Playlist Assistant data while keeping the normal view compact.

## UI model

Use optional **column groups** rather than primarily expanding individual rows. Analytical work usually compares the same property across the complete table.

Suggested groups:

- **Playback** — play count, first played, last played, days since last play, known-for duration, average interval between plays.
- **Selection** — Rare score, Long score, combined score, rank, current selection status.
- **Sources** — source playlist names, source count, current source membership.
- **Track** — album, duration, Spotify ID/URI and other already available base data.
- **Metadata** — later: year, ISRC, genres, tags.
- **Audio Features** — later: energy, danceability, valence, acousticness, instrumentalness, tempo, loudness and similar values.
- **Classification** — later: mood groups, smart groups, user tags.
- **Data Quality** — later: provider, match confidence, enrichment freshness and provenance.

All useful analytical columns should be sortable and filterable where practical.

## Derived data without external providers

Several useful fields can be calculated from existing Playlist Assistant data before any metadata provider is added, including first played, known-for duration, average listening interval, source count, score components and selection rank.

## Explainability

A later analytical view should make it possible to understand why a track was selected: source, score components, ranking and profile/classification rules where relevant.

## Home Assistant boundary

Detailed columns belong in Playlist Assistant. Only aggregate values that later prove useful for automations or dashboards should become Home Assistant sensors.