# Playlist Assistant

Playlist Assistant brings music you already like back into rotation. It builds
a private Spotify playlist from your selected sources and listening history.

## Sources

Mark Spotify source playlists with `#today-source`. The app uses only those
playlists when it prepares a selection.

## Selection settings

Rare weighting favours tracks with fewer known plays. Artist Gap keeps the
configured number of tracks between appearances by the same artist. Sync
history refreshes the listening history used for both decisions.

## Preview, publish, and schedule

Preview calculates the next playlist without changing Spotify. Publish writes
the current preview to the private target playlist. A enabled schedule lets
Home Assistant run the daily workflow at the selected time.

## Last played

Last-played values are shown relative to your local time. Hover over a value
to see its exact local timestamp.
