# Direct Playback and Play/Save Outputs

Status: Idea
Priority: P1
Area: Playback
Depends on: Beta stability

## Goal

Treat direct Spotify playback as a primary output of a generated selection instead of requiring the user to open a generated Spotify playlist manually.

## Product model

A concrete selection can have two separate outputs:

- **Play** — start that exact selection through Spotify playback.
- **Save** — persist that exact selection as a Spotify playlist, with a user-defined name or an existing managed target.

Play and Save must not independently recalculate the selection.

## Spotify considerations

Prefer starting playback from the selected track URIs over trying to build a large Spotify queue one item at a time. Spotify playback/device capability and Premium requirements must be verified during implementation.

## Home Assistant

Direct playback should eventually be available as a Home Assistant action so it can be placed beside ordinary media-player controls in a dashboard.

Likely useful actions are Play current selection and Generate/New selection. Saving a playlist is more naturally a Playlist Assistant UI action unless a concrete automation use case emerges.

## Open questions

- Device selection versus currently active Spotify Connect device.
- Exact behavior when no controllable device is available.
- OAuth scopes and capability reporting.
- How playback should behave when part of a daily selection was already heard.