# Playlist Assistant

Playlist Assistant brings music you already like back into rotation. It builds
a private Spotify playlist from your selected sources and listening history.

## Sources

Mark Spotify source playlists with `#today-source`. The app uses only those
playlists when it prepares a selection.

## Selection settings

The weighting slider keeps **Long not played** on the left and **Rarely
played** on the right. The displayed values always total 100: the stored Rare
value is shown on the right and the derived Long value (`100 - Rare`) is shown
on the left. Moving the slider saves configuration only. Select Preview or run
the full workflow to recalculate the visible track selection.

Rare weighting favours tracks with fewer known plays. Artist Gap keeps the
configured number of tracks between appearances by the same artist. Sync
history refreshes the listening history used for both decisions.

## Preview, publish, and schedule

Preview calculates the next playlist without changing Spotify. Publish writes
the current preview to the private target playlist. A enabled schedule lets
Home Assistant run the daily workflow at the selected time.

The compact status beneath Actions uses the existing successful job
timestamps. Listening history shows the last successful History update, and
daily/full execution shows the last successful complete run. A clean
never-run value is shown until the corresponding job has completed.

## Last played

Last-played values are shown relative to your local time. Hover over a value
to see its exact local timestamp.
