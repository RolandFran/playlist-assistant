# Playlist Assistant Design Principles

Status: authoritative product and UX principles

## Keep detailed music intelligence inside Playlist Assistant

Playlist Assistant owns detailed music data, analysis, selection logic, source relationships, metadata enrichment, classifications, and track-level views.

Home Assistant is the control and automation surface. It should expose only deliberately chosen actions, concise status, and useful aggregate sensors.

Do not represent large track-level datasets as large numbers of Home Assistant entities.

New metrics should first be implemented and evaluated inside Playlist Assistant. Only metrics that prove useful for Home Assistant automations or dashboards should later become sensors.

## Selection is not output

The user should be able to inspect one concrete selection and then decide what to do with that exact result.

Primary output actions are:

- **Play** — play the selection directly.
- **Save** — save the selection as a Spotify playlist.

Play and Save must operate on the same selection rather than independently recomputing it.

## Keep the normal UI simple and make analysis optional

The primary track table should remain compact. Additional analytical information should be exposed through optional **column groups**, not primarily through per-row expansion.

A user who enables an analytical dimension usually wants to compare that dimension across the complete table. Column groups should therefore support sorting and filtering across all tracks.

Potential groups include Playback, Selection, Sources, Track, Metadata, Audio Features, Classification, and Data Quality.

## Explain selections

Playlist Assistant should favor transparent selection logic. Where useful, the UI should make it possible to understand why a track was selected, including score components, source, ranking, and later metadata or profile rules.

## Preserve enriched knowledge

Metadata belongs to the track/catalog layer, not to an individual playlist membership. Removing a playlist from active sources must not delete already acquired enrichment for tracks that were previously relevant.

## External metadata must remain replaceable

Provider-specific data should be normalized behind a provider-independent model and retain provenance where practical. The selection engine and UI should not depend directly on one provider's schema.

## Stability before expansion

Beta stabilization has precedence over new product features. Future documentation exists to avoid architectural dead ends and preserve decisions, not to expand the current implementation scope prematurely.