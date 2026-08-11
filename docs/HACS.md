# HACS distribution

## Repository layout

Playlist Assistant uses the standard HACS integration layout:

- `hacs.json` is in the repository root.
- The single custom integration is in `custom_components/playlist_assistant/`.
- The Home Assistant manifest contains the required domain, name,
  documentation, issue tracker, code owners, and integration version.

No `content_in_root`, `zip_release`, or custom release artifact is needed.

## Brand asset still required

No suitable Playlist Assistant project logo exists in the repository yet. Do
not substitute a generic placeholder. Before publishing the first integration
release, add an approved square PNG icon as:

`brand/icon.png`

This is the `brand` directory inside the custom integration, where HACS looks
for local custom-integration brand assets. The icon should follow the current
Home Assistant brand-image requirements.

## GitHub repository settings

The public GitHub repository must have Issues enabled, a concise description,
and relevant topics. Recommended values are:

- Description: `Home Assistant integration and app for building a private, automatically refreshed Spotify Today playlist.`
- Topics: `home-assistant`, `hacs`, `custom-integration`, `spotify`,
  `playlist`, `home-assistant-addon`

These settings are maintained in GitHub and are not represented by files in
the repository.

## Release policy

GitHub Releases for this repository currently represent only releases of the
custom integration. The GitHub tag and release version must match the version
in `custom_components/playlist_assistant/manifest.json`, prefixed with `v`:

- Integration `0.3.0` is released as tag and GitHub Release `v0.3.0`.
- A subsequent integration `0.3.1` is released as `v0.3.1`.

The Home Assistant app version remains independent and continues to be
maintained separately in the app configuration. Do not publish GitHub Releases
with app version numbers: HACS interprets repository releases as integration
versions.

No GitHub Release is created as part of the HACS preparation itself.
