"""Application credentials for the Playlist Assistant Spotify OAuth flow."""
from homeassistant.components.application_credentials import ClientCredential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import LocalOAuth2Implementation

from .const import (
    SPOTIFY_AUTHORIZE_URL,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_TOKEN_URL,
)


class SpotifyOAuth2Implementation(LocalOAuth2Implementation):
    """Spotify implementation using Home Assistant-managed credentials."""

    @property
    def redirect_uri(self) -> str:
        """Use My Home Assistant's public OAuth relay for local HA installs."""
        return SPOTIFY_REDIRECT_URI


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> SpotifyOAuth2Implementation:
    """Build an OAuth implementation from Home Assistant's credential store."""
    return SpotifyOAuth2Implementation(
        hass,
        auth_domain,
        credential.client_id,
        credential.client_secret,
        SPOTIFY_AUTHORIZE_URL,
        SPOTIFY_TOKEN_URL,
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return links used by the credentials dialog."""
    return {
        "spotify_developer_dashboard_url": "https://developer.spotify.com/dashboard",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }
