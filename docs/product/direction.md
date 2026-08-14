# Playlist Assistant Product Direction

Status: authoritative product direction

Playlist Assistant is not merely a generator for one Spotify playlist named `Today`. `Today` is a useful default and current implementation, not the product definition.

The long-term purpose is to help users hear music they already know they like, control how that music is selected, and maintain and protect their Spotify listening environment over time.

## Core product model

The central product object is a **selection**: a concrete ordered set of tracks produced from user-defined sources, listening history, metadata, and selection rules.

A selection is distinct from its output.

- **Play** starts the current selection directly through Spotify playback.
- **Save** persists the current selection as a Spotify playlist.

A Spotify playlist is therefore one possible output of Playlist Assistant, not the internal definition of a selection.

## Profiles

A profile describes how a selection should be built. Profiles may later combine source playlists, scoring, genre or mood groups, exclusions, artist spacing, size, and other rules.

The same profile may be used once or on a schedule. A daily selection is one scheduled form of the same model rather than a separate product concept.

## Daily use

For a daily profile, Playlist Assistant may create one fixed daily selection. Replaying it later should use the still-unheard remainder of that selection. A manual New action may explicitly discard and regenerate it. The next scheduled day creates the next selection.

A continuously replenished radio queue is not required for this use case; daily regeneration already provides a bounded rolling mechanism.

## Personal music catalog

Listening history and selection eligibility are separate concepts.

- Listening history may contain every observed play.
- A track becomes relevant for metadata enrichment when it has occurred in an included/source playlist at least once.
- Once a track has become relevant, its enriched metadata should not be discarded merely because that playlist is later removed from the active selection sources.

Source playlists determine eligibility; they do not own track metadata.

## Product areas

Long-term product areas include:

- Discover and rediscover
- Selection and control
- Play and save
- Profiles, genres, moods, and smart grouping
- Repair of unavailable or replaced tracks
- Playlist protection and backup
- Insights and listening statistics
- Data quality and history integrity
- Track identity, metadata, and provenance

These areas describe direction only. The current development priority remains Beta stabilization.