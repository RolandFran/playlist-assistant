# Playlist Assistant Home Assistant app

This directory is a custom Home Assistant app package for Playlist Assistant.
It starts one small supervised Python service after Home Assistant has started
(`startup: application`). The service invokes the existing `SchedulerPolicy`
once per minute; it does not contain another scheduler or Spotify pipeline.

## Ingress control panel

Home Assistant Ingress provides the authenticated daily control panel. It
shows Spotify/last-job/scheduled status, current Today data, and the normal
persisted settings. The page uses the Home Assistant browser language when it
is German and otherwise uses English. It exposes no host port or general LAN
API; the internal listener accepts only the Supervisor Ingress proxy.

The panel can collect history, sync sources, calculate a local Today result,
or publish Today. Spotify-dependent buttons explain why they are unavailable
when authorization is missing. Changing the target playlist name keeps its
persisted Spotify ID and real publishing renames that same playlist instead
of creating another one.

## Install for local testing

Do not copy these files into an existing configuration unless you deliberately
want to test the app. For a development Home Assistant installation, add this
repository as a local/custom app repository using the Supervisor's normal
custom-repository flow, then install **Playlist Assistant**. The package has
no `/config`, Node-RED, host-device, dashboard, automation, or integration
dependency.

The container build can also be checked without Home Assistant from the
repository root with `docker build -f ha_app/Dockerfile .`. This repository
does not install or modify anything on a Home Assistant instance.

## Configuration and secrets

The app configuration contains:

- `spotify_client_id`: Spotify Developer client ID.
- `spotify_client_secret`: sensitive/masked Spotify Developer client secret.

Neither value is committed, written to the project code, returned by the
health endpoint, or logged. The start script reads Supervisor's private
`/data/options.json` directly, and the service supplies the values only as
process environment for the existing engine.

Browser authorization, a callback, token-copying options, and re-authorization
are intentionally not implemented. Until an existing usable authorization
cache is available, the service stays up with `spotify_status=not_connected`,
pauses scheduler jobs, and reports a healthy watchdog response. It checks
again on its normal one-minute tick, not in a tight retry loop.

## Persistent data, logs, and health

All runtime persistence stays under `/data` through `ApplicationPaths`:

- `/data/playlist_assistant.db` is the one production database.
- `/data/reports/` holds engine reports.
- `/data/spotify-oauth-cache.json` is the Spotify token cache.
- `/data/spotify-authorization-status.json` contains non-secret connection
  status metadata.

The app launches the engine with `--data-dir /data`; it never falls back to
the application-code directory. Structured lifecycle, scheduler, and job
errors go to stdout/stderr and therefore appear in the Home Assistant app log.
`GET /health` on the internal app network returns only a small connection
status JSON document for the Supervisor watchdog. It is not a user-facing or
LAN API and no port is published by this package.

## Deferred work

This foundation intentionally defers entities, services, custom cards, browser
Spotify authorization/re-authorization, backup/restore, and any changes to
existing Home Assistant or Node-RED configuration.
