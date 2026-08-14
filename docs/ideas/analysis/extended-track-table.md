# Erweiterte Analyse-Tabelle mit Spaltengruppen

**Status:** Idee  
**Priorität:** P1  
**Bereich:** UI / Analyse  
**Voraussetzung:** Beta-Stabilität

## Ziel

Die bestehende Track-Tabelle soll zur zentralen Analyseansicht für detaillierte Playlist-Assistant-Daten werden, ohne die normale Ansicht zu überladen.

## UI-Modell

Zusätzliche Informationen werden bevorzugt über optionale **Spaltengruppen** eingeblendet, nicht über das Aufklappen einzelner Track-Zeilen. Bei Analysen interessiert meist dieselbe Eigenschaft für die gesamte Tabelle.

Vorgesehene Gruppen:

- **Wiedergabe** – Play Count, First Played, Last Played, Tage seit letztem Play, bekannte Zeitspanne, durchschnittlicher Abstand zwischen Plays.
- **Selection** – Rare Score, Long Score, Gesamt-Score, Rang, aktueller Selection-Status.
- **Sources** – Namen der Source-Playlists, Anzahl Sources, aktuelle Source-Mitgliedschaft.
- **Track** – Album, Dauer, Spotify ID/URI und weitere bereits vorhandene Basisdaten.
- **Metadaten** – später: Jahr, ISRC, Genres, Tags.
- **Audio Features** – später: Energy, Danceability, Valence, Acousticness, Instrumentalness, Tempo, Loudness und ähnliche Werte.
- **Klassifikation** – später: Mood-Gruppen, Smart Groups, eigene Tags.
- **Datenqualität** – später: Provider, Match Confidence, Aktualität des Enrichments und Provenance.

Sinnvolle Analyse-Spalten sollen soweit praktikabel sortier- und filterbar sein.

## Bereits ohne externen Provider möglich

Mehrere interessante Werte lassen sich schon aus vorhandenen Playlist-Assistant-Daten gewinnen, zum Beispiel:

- First Played
- Known For / Zeit seit dem ersten bekannten Play
- durchschnittlicher Abstand zwischen Wiedergaben
- Source Count
- Rare Score und Long Score getrennt
- Gesamt-Score
- Selection Rank
- aktuelle bzw. frühere Source-Beziehung, soweit im Datenmodell vorhanden

Damit kann die App bereits deutlich informativer werden, bevor ein Metadata Provider implementiert wird.

## Nachvollziehbarkeit

Die Analyseansicht soll später erklären können, warum ein Track ausgewählt wurde: Source, Score-Komponenten, Rang und – sobald vorhanden – Profil-, Genre- oder Klassifikationsregeln.

## Home-Assistant-Grenze

Die detaillierten Spalten gehören in Playlist Assistant. Nur aggregierte Werte, die sich später als nützlich für Automationen oder Dashboards erweisen, werden gezielt als Home-Assistant-Sensoren exponiert.

## Erweiterbarkeit

Die Tabellenkomponente soll neue Datenfelder möglichst deklarativ aufnehmen können. Provider-Daten sollen später lediglich weitere Spalten bzw. Spaltengruppen ergänzen, ohne dass die Tabellenarchitektur neu gebaut werden muss.