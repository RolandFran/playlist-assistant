# Mehrere Accounts und Capability Handling

**Status:** Idee  
**Priorität:** P3  
**Bereich:** Accounts / Capabilities  
**Voraussetzung:** stabile Single-Account-Beta

## Ziel

Mehrere Spotify-Accounts können langfristig betrachtet werden, ohne heute bereits Multi-Account-Infrastruktur vorwegzuimplementieren.

## Capabilities

Bestimmte Funktionen können abhängig sein von:

- Spotify Premium
- gewährten OAuth Scopes
- verfügbaren Spotify-Web-API-Funktionen
- verfügbaren Metadata Providern
- Playback-Geräten bzw. Provider-Fähigkeiten

Eine spätere UI kann verständlich anzeigen, welche Funktionen für den aktuell verbundenen Account tatsächlich verfügbar sind.

## Leitlinie

Der heutige Single-Account-Kern wird nicht durch vorsorgliche Multi-Account- oder Feature-Flag-Komplexität belastet. Erst ein konkreter Bedarf rechtfertigt diese Erweiterung.