#!/usr/bin/with-contenv bashio
set -euo pipefail

# Remove retired options through Supervisor so its persisted configuration and
# /data/options.json stay in sync. Do not echo option values.
options="$(bashio::addon.options)"
for legacy_option in spotify_client_id spotify_client_secret bridge_token; do
  if bashio::jq.exists "${options}" ".${legacy_option}"; then
    bashio::log.info "Removing obsolete add-on option: ${legacy_option}"
    bashio::addon.option "${legacy_option}"
  fi
done

exec python3 /app/service.py \
  --data-dir /data \
  --options-file /data/options.json
