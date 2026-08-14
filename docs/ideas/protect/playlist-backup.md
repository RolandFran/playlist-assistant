# Playlist-Backup und Schutz

**Status:** Idee  
**Priorität:** P3  
**Bereich:** Protect  
**Voraussetzung:** stabile Spotify-Write-Funktionen

## Ziel

Spotify-Playlists sollen vor versehentlichen oder problematischen Änderungen geschützt und bei Bedarf wiederhergestellt werden können.

Playlist-Backups sind ausdrücklich etwas anderes als Home-Assistant-App-Backups.

## Snapshot-Inhalt

Ein Playlist-Snapshot kann unter anderem enthalten:

- Reihenfolge/Position
- Spotify Track ID/URI
- Titel
- Artist
- Album
- ISRC, soweit vorhanden
- Zeitpunkt des Snapshots

## Funktionen

- manuelles Backup
- automatische Snapshots vor riskanten Write-/Repair-Aktionen
- Restore mit vorheriger Preview/Diff
- vor einem Restore automatisch den aktuellen Zustand sichern
- Export/Download
- Retention-Regeln

Das Backup-System soll die Spotify-Playlist schützen; die Sicherung der Playlist-Assistant-App und ihrer Datenbank bleibt Aufgabe der Home-Assistant-Backup-Mechanismen.