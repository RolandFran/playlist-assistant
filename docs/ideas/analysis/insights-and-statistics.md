# Insights und Statistiken

**Status:** Idee  
**Priorität:** P2  
**Bereich:** Analyse  
**Voraussetzung:** Beta-Stabilität

## Ziel

Statistiken sollen nicht nur dekorativ sein, sondern helfen, das Hörverhalten zu verstehen und die Qualität der Selection Engine zu beurteilen.

## Denkbare Auswertungen

- Wiedergaben über die Zeit
- Top Tracks und Artists
- unterschiedliche Tracks/Artists pro Zeitraum
- Source-/Katalog-Abdeckung
- selten gehörte und lange nicht gehörte Tracks
- Rediscovery nach 30, 90, 180 oder 365 Tagen
- Artist-, Genre- und Source-Verteilung
- Vergleich von Kandidatenpool und erzeugter Selection
- Hinweise auf Dominanz einzelner Artists/Genres
- Entwicklung der Selection-Qualität und der Score-Verteilung

## Bestehende Daten nutzen

Viele Analysen lassen sich bereits aus History, Sources und Scoring ableiten. Providerdaten können später zusätzliche Dimensionen wie Genre, Mood und Audio Features ergänzen.

## UI

Ein Teil der Analyse erfolgt direkt über die erweiterte Track-Tabelle. Für zeitliche Entwicklungen und Verteilungen können später eigene Diagramme oder kompakte Insight-Ansichten ergänzt werden.

## Home Assistant

Detaillierte Analyse bleibt in Playlist Assistant. Nur wenige aggregierte Kennzahlen werden später bei konkretem Automations-/Dashboard-Nutzen als HA-Sensoren bereitgestellt.