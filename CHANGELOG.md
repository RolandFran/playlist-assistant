# Changelog

## Integration 0.3.6-beta.10 and add-on 0.1.33

Beta stabilization and reliability release. The production Home Assistant
schedule callbacks now use the async execution behavior validated by the
HA-tested Historical Test implementation. The Spotify publish path remains
aligned with that proven implementation, including Home Assistant-owned OAuth
session reuse, persisted target handling, privacy/name updates only when
needed, and full playlist replacement.

This release does not claim to identify the previous HTTP 502 root cause.
