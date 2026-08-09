#!/usr/bin/with-contenv bashio
set -euo pipefail

# Do not echo /data/options.json: it contains Spotify credentials.
exec python3 /app/ha_app/service.py \
  --data-dir /data \
  --options-file /data/options.json
