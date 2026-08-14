# Genres, Mood-Gruppen und Smart Grouping

**Status:** Idee  
**Priorität:** P2  
**Bereich:** Klassifikation / Selection  
**Voraussetzung:** Metadata-Enrichment und Profile

## Ziel

Tracks sollen später nicht nur über Source und Hörhistorie, sondern auch über musikalische Merkmale gruppiert und ausgewählt werden können.

Beispiele für Gruppen oder Profile:

- Ruhige Songs
- Upbeat
- Rock & Alternative
- Jazz
- Classical
- French / Chanson

## Genres

Mögliche Funktionen:

- Genres einschließen oder ausschließen
- mehrere Genres zu einer eigenen Gruppe zusammenfassen
- Genre-Verteilung innerhalb einer Selection ausbalancieren
- Genre-Verteilung von Source-Pool und Ergebnis vergleichen

## Mood-Gruppen

Eine Mood-Gruppe ist eine Playlist-Assistant-Klassifikation, die mehrere Genres, Tags und später Audio Features kombinieren kann.

Beispiel `Ruhig`: passende Genres/Tags plus später niedrige Energy/Arousal-Werte, sofern solche Daten verfügbar sind.

## Smart Grouping

Playlist Assistant kann später auf Basis der tatsächlich im persönlichen Musikkatalog vorhandenen Genres, Tags und Features sinnvolle Gruppen vorschlagen.

Vorschläge sind keine Wahrheit und werden nicht ungefragt als feste Klassifikation übernommen. Der Nutzer kann Gruppen bestätigen, umbenennen und ihre Bestandteile ändern.

## Datenquellen

Spotify-Metadaten können verwendet werden, soweit verfügbar. Reichen diese nicht aus, werden zusätzliche Metadata Provider genutzt. Audio Features sind eine separate Erweiterung.

Die Klassifikation soll provider-unabhängig bleiben.