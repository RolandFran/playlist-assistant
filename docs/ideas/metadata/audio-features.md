# Audio Features und Sonic Analysis

**Status:** Idee  
**Priorität:** P2  
**Bereich:** Metadaten / Audioanalyse  
**Voraussetzung:** Provider-Grundgerüst

## Ziel

Musikalische Eigenschaften sollen später für Analyse, Mood-Gruppen und Selection-Regeln verfügbar sein.

Interessante Werte sind insbesondere:

- Energy
- Danceability
- Valence
- Acousticness
- Instrumentalness
- Liveness
- Speechiness
- Tempo
- Loudness
- gegebenenfalls Arousal, Brightness, Harmonic Complexity und ähnliche Analysewerte

## Spotify

Spotify stellte solche Audio Features früher über die Web API bereit. Für neue bzw. normale Development-Mode-Anwendungen sind diese Endpunkte heute nicht zuverlässig als Produktgrundlage verfügbar. Playlist Assistant soll deshalb nicht davon abhängig sein.

## Externe Provider zuerst prüfen

Bevor eine eigene Audioanalyse gebaut wird, soll geprüft werden, welche Abdeckung sich über Metadata Provider für die tatsächlich relevanten Tracks erreichen lässt.

Providerwerte werden im gleichen provider-unabhängigen Track-Feature-Modell gespeichert und mit ihrer Herkunft versehen.

## Sonic Analysis als spätere Option

Music Assistant zeigt, dass lokale Audioanalyse Features und Ähnlichkeitswerte erzeugen kann. Eine eigene bzw. adaptierte Sonic-Analyse wäre jedoch deutlich aufwendiger als reines Metadata-Enrichment und setzt Zugriff auf eine zulässige Audioquelle voraus.

Für reine Spotify-Tracks besitzt Playlist Assistant nicht automatisch die vollständigen Audiodaten. Deshalb ist Sonic Analysis derzeit eine spätere Option und kein bevorzugter erster Weg.

Falls Music Assistant später selbst als Datenquelle dienen kann und Analysewerte über eine geeignete Schnittstelle verfügbar sind, sollte auch die Übernahme bereits berechneter Werte geprüft werden, statt dieselben Tracks erneut zu analysieren.