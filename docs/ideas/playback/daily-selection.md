# Daily Selection Model

Status: Idea
Priority: P1
Area: Playback / Scheduling
Depends on: Beta stability, direct playback foundation

## Goal

Generalize the current `Today` behavior into one fixed daily selection that can be played, resumed by rebuilding the unheard remainder, manually regenerated, or saved as a Spotify playlist.

## Proposed behavior

At the configured daily time, Playlist Assistant creates one concrete selection, for example 200 tracks.

- **Play** sends the currently unheard remainder of that day's selection to Spotify.
- **New** explicitly discards/regenerates the current daily selection using the latest history and rules.
- **Save** persists the current selection as a Spotify playlist.
- The next scheduled day creates a new daily selection.

Example: 200 tracks are generated, 20 are heard, and the user later starts another Spotify playlist. Pressing Play again should restore the remaining 180 tracks rather than append 20 newly selected tracks.

## Non-goal

Do not add a continuously replenished radio queue by default. Daily regeneration already gives a bounded rolling mechanism and keeps the model understandable.

## Data requirement

The concrete daily selection must remain persistent in Playlist Assistant even when no Spotify playlist is created. The system must be able to identify which tracks from that selection have already been heard during its lifetime using the existing listening-history model.

## Home Assistant

The useful dashboard-facing controls are intentionally small: Play current selection and New selection. Detailed selection management stays in Playlist Assistant.