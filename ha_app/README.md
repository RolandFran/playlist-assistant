# Playlist Assistant Home Assistant app

This directory is a custom Home Assistant app package for Playlist Assistant.
It starts one small supervised Python service after Home Assistant has started
(`startup: application`). It hosts only the Ingress application and connection
reporting. The companion `playlist_assistant` custom integration owns native
Home Assistant scheduling, actions, and entities; the app/engine owns every
Spotify and pipeline operation.

The add-on build context is this directory only. Its dependency manifest and
the engine modules used by `service.py` are packaged here alongside the
Ingress files, so Supervisor builds never depend on repository-root paths.
When engine code changes, update the matching packaged module in this
directory as part of the same change.

## Ingress control panel

Home Assistant Ingress provides the authenticated daily control panel. It
shows Spotify/last-job/scheduled status, current Today data, and the normal
persisted settings. The page uses the Home Assistant browser language when it
is German and otherwise uses English. It exposes no host port or general LAN
API; the internal listener accepts only the Supervisor Ingress proxy.

The panel workflow is **save settings → connect Spotify → Preview → inspect → Publish**.
It can sync history, create a persisted preview, publish a current preview,
or run the complete pipeline. Source synchronization is deliberately internal
to a complete run. Spotify-dependent buttons explain why they are unavailable
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

## Home Assistant integration

Copy `custom_components/playlist_assistant/` from this repository to
`/config/custom_components/playlist_assistant/`, restart Home Assistant, then
add **Playlist Assistant** from Settings → Devices & services. Enter the
add-on's internal URL (`http://playlist_assistant:8098`) and the same
`bridge_token` configured in the add-on options. The URL is Docker-network
internal and the add-on publishes no host port. The token is used only in the
`X-Playlist-Assistant-Bridge` header and never exposes Spotify credentials or
OAuth cache data.

The add-on sends schedule-change events to HA Core through the authenticated
Supervisor Core API. The integration listens for that event and replaces its
native callbacks immediately; no polling, shared Python objects, or LAN API is
used.

`homeassistant_api: true` is required so the add-on can use that authenticated
Supervisor Core API event endpoint. It grants only the Supervisor-proxied Core
API access needed for schedule-change events; it does not publish a host port
or expose the private bridge outside Home Assistant's internal network.

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

Saving settings does not authorize Spotify. When Spotify is not connected, the
Ingress panel shows a **Connect Spotify** action and the exact redirect URI to
register in the Spotify Developer Dashboard. Register that URI verbatim (it
contains the current Home Assistant Ingress path), then use the button. The
browser returns through Ingress, where the add-on exchanges the authorization
code and stores only Spotify's token cache under `/data`. The panel then shows
Spotify as connected and enables Spotify actions. Client secret, bridge token,
authorization code, and access/refresh tokens are never shown or logged.

Until authorization is completed, the service stays up with
`spotify_status=not_connected` and reports a healthy watchdog response. It
does not poll or schedule pipeline work itself.

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
