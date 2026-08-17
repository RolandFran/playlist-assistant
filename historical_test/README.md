# Playlist Assistant Historical Test

This package is an isolated diagnostic variant built from the historical
baseline `94c38a398efda38f84f2604fc76da9f68314e88f`.  It exists solely for one
manual Home Assistant-to-Spotify Publish comparison.  It is not a production
upgrade and must not be used to replace the normal Playlist Assistant.

## Contents

- `playlist_assistant_historical_test/` is a Home Assistant add-on with slug
  `playlist_assistant_historical_test`, Ingress port `8108`, watchdog port
  `8109`, and a separate database named
  `playlist_assistant_historical_test.db`.
- `custom_components/playlist_assistant_historical_test/` is the matching
  historical custom integration.  Its separate domain, service names, and
  Spotify proxy endpoint prevent it from using the production integration.

The add-on's `/data` mount is isolated by its unique slug.  It therefore does
not share the production add-on's database, reports, OAuth state, or options.
The separate integration domain also gives the test its own HA config entry,
entities, services, and proxy endpoint.

## Controlled test installation

1. Keep the existing production Playlist Assistant add-on and integration
   installed and running; do not replace either directory.
2. Copy `historical_test/playlist_assistant_historical_test/` to
   `/addons/playlist_assistant_historical_test/` on the Home Assistant host.
   This uses Home Assistant's local app mechanism; do not add this repository
   as a custom app repository.
3. Refresh or reload the Home Assistant App Store. Install **Playlist Assistant
   Historical Test** from the **Local apps** section.
4. Copy `historical_test/custom_components/playlist_assistant_historical_test/`
   to `/config/custom_components/playlist_assistant_historical_test/` alongside
   the production `playlist_assistant` directory, then restart Home Assistant
   Core so it discovers the new integration.
5. Add **Playlist Assistant Historical Test** in Settings > Devices & services
   and complete its separate Spotify authorization.  Its add-on discovery and
   proxy endpoint use only the historical-test identifiers.
6. Open the historical-test add-on Ingress page.  Set a dedicated disposable
   Spotify target playlist; the safe default is `Playlist Assistant Historical
   Test`, never `Today`.  Do not select the production Today playlist.
7. Run Sync, Preview, then manually Publish.  Record the full result,
   including whether metadata handling and complete playlist replacement
   succeed, the track count, Spotify request count, and any error response.

The historical Spotify/auth/publish implementation has not been forward-ported
or repaired.  The only intentional code differences are coexistence identifiers
(name, slug, domain, endpoint, ports, paths, and labels) plus the safe target
playlist default.
