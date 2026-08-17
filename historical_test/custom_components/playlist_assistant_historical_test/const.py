"""Constants for the Playlist Assistant Historical Test integration."""

DOMAIN = "playlist_assistant_historical_test"
PANEL_ICON = "mdi:play"
PLATFORMS = ["sensor", "binary_sensor"]
HISTORY_GRACE_MINUTES = 15

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_ME_URL = "https://api.spotify.com/v1/me"
SPOTIFY_REDIRECT_URI = "https://my.home-assistant.io/redirect/oauth"
SPOTIFY_SCOPE = " ".join((
    "user-read-private", "user-read-recently-played", "playlist-read-private",
    "playlist-read-collaborative", "playlist-modify-private", "playlist-modify-public",
))
