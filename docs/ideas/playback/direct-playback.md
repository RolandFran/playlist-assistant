# Direktes Abspielen und Play/Save

**Status:** Idee  
**Priorität:** P1  
**Bereich:** Playback / Output  
**Voraussetzung:** Beta-Stabilität

## Ziel

Eine erzeugte Selection soll nicht zwingend zuerst als Spotify-Playlist veröffentlicht werden müssen. Der Nutzer soll mit derselben konkreten Selection zwei getrennte Möglichkeiten haben:

- **Play** – direkt über Spotify abspielen.
- **Save** – dauerhaft als Spotify-Playlist speichern.

Damit wird die ursprüngliche Kernidee des Playlist Assistant direkter umgesetzt: Musik auswählen, die der Nutzer wieder hören möchte, und diese Auswahl unmittelbar abspielen.

## Leitlinien

- **Selection und Output sind getrennt.**
- Play und Save arbeiten auf exakt derselben Selection.
- Save darf nicht still eine andere Selection neu berechnen.
- Eine Spotify-Playlist ist ein optionaler dauerhafter Output, nicht der technische Speicher der Selection.
- Die Selection selbst bleibt im Playlist Assistant verfügbar.

## Home Assistant

Für Home Assistant ist insbesondere **Play** als Action interessant, damit die aktuelle Selection direkt aus einem Dashboard oder einer Automation gestartet werden kann.

Detaillierte Trackdaten bleiben im Playlist Assistant; Home Assistant dient nur als Steuerungsebene.

## Offene technische Fragen

- Welche Spotify-Playback-/Queue-API-Kombination ist für eine größere Selection robust genug?
- Wie werden aktives Spotify-Gerät und fehlendes verfügbares Playback-Device behandelt?
- Welche Premium-/Scope-Anforderungen gelten beim tatsächlichen Implementierungszeitpunkt?

Diese Fragen werden erst bei der konkreten Umsetzung entschieden.