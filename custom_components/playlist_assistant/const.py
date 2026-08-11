"""Constants for the Playlist Assistant integration."""

DOMAIN = "playlist_assistant"
PLATFORMS = ["sensor", "binary_sensor"]
HISTORY_GRACE_MINUTES = 15

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_ME_URL = "https://api.spotify.com/v1/me"
SPOTIFY_REDIRECT_URI = "https://my.home-assistant.io/redirect/oauth"
SPOTIFY_SCOPE = "user-read-private"
