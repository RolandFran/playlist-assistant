# Playlist Assistant

Playlist Assistant erstellt aus ausgewählten Spotify-Quellplaylists automatisch eine dynamische Playlist `Today`.

Quellen werden über den Marker `#today-source` in der Spotify-Playlistbeschreibung erkannt. Die Auswahl wird anhand einer Kombination aus Seltenheit der Wiedergabe, Zeit seit dem letzten Hören und Künstlerabstand erzeugt.

## Aktueller Stand

Der aktuelle Stand läuft lokal als Python-Anwendung. Zielplattform ist eine Home-Assistant-App mit eigener Oberfläche für Konfiguration, Status, manuelle Aktionen und die erzeugte Playlist.

Aktuell vorhanden:

- Spotify-Recently-Played-Collector
- inkrementeller Source-Sync über `snapshot_id`
- SQLite-Datenbank `playlist_assistant.db`
- URI-first Matching gegen die Hörhistorie
- Rare-, Long- und Combined-Scoring
- Artist-Min-Gap bei der Today-Auswahl
- Stale-Result-Sicherung vor dem Publish
- privates Publish der Zielplaylist `Today`
- zentraler CLI-Einstieg über `run.py`

## Voraussetzungen

- Python 3
- Spotify-Developer-Zugang / OAuth-Konfiguration
- Python-Abhängigkeiten des Projekts

Lokale Secrets gehören in `.env` und werden nicht versioniert.

## Schnellstart

Die wichtigsten Einzeljobs:

```powershell
python run.py history
python run.py sources
python run.py score
python run.py publish
```

Die Scoring-Werte können pro Lauf explizit übergeben werden. Nicht angegebene
Werte bleiben bei den Standardwerten:

```powershell
python run.py score --today-size 100 --rare-weight 70 --artist-min-gap 5
```

Dieselben Optionen stehen für `python run.py today` zur Verfügung und werden
an den Scoring-Schritt weitergereicht.

Komplette Today-Pipeline:

```powershell
python run.py today
```

Spotify-Schreibzugriff erfolgt bewusst nicht automatisch. Für einen echten Publish:

```powershell
python run.py today --write
```

## Standardwerte

```text
Today-Größe:      200
Rare-Gewichtung:   50
Long-Gewichtung:   50
Artist-Min-Gap:    10
```

Nur die Rare-Gewichtung ist konfigurierbar. Die Long-Gewichtung wird immer als
Gegenwert berechnet, sodass beide zusammen 100 ergeben.

## Datenfluss

```text
collector.py
    ↓
sync.py
    ↓
scoring.py
    ↓
publish.py
```

`run.py` führt diese Schritte für `today` in der Reihenfolge History → Sources → Scoring → Publish aus.

## Wichtige Dateien

- `run.py` – zentraler CLI-Einstieg
- `client.py` – zentrale Spotify-/Spotipy-Grenze
- `collector.py` – Recently-Played-Sync
- `sync.py` – Source- und Playlist-Synchronisierung
- `scoring.py` – Matching, Scoring und Today-Auswahl
- `publish.py` – Frischeprüfung und Spotify-Publish
- `db_state.py` – Zustandsfingerprint für die Stale-Result-Sicherung
- `PROJECT.md` – aktueller verbindlicher Projektstand
- `docs/docs-design-notes.md` – Architecture Decision Log

## Lokale, nicht versionierte Daten

Unter anderem werden nicht ins Repository aufgenommen:

- `.env`
- Spotify-OAuth-Token und Cache-Dateien
- `playlist_assistant.db`
- `reports/`
- `import/`
- lokale Backups und Python-Caches

## Dokumentation

Für Entwicklung und Architektur gelten zwei Dokumente mit unterschiedlichen Rollen:

- [`PROJECT.md`](PROJECT.md) beschreibt den aktuell verbindlichen Soll- und Projektstand.
- [`docs/docs-design-notes.md`](docs/docs-design-notes.md) dokumentiert Architekturentscheidungen und deren Entwicklung.

Bei Widersprüchen zwischen einem älteren ADR und `PROJECT.md` gilt der in `PROJECT.md` dokumentierte aktuelle Stand.

## Entwicklungsworkflow

`main` ist der stabile, freigegebene Stand. Änderungen erfolgen in separaten Branches und werden über Pull Requests geprüft, bevor sie nach `main` gemergt werden.

Nach einem freigegebenen Merge wird der lokale Stand mit folgendem Befehl aktualisiert:

```powershell
git pull
```

## Home Assistant

Die Home-Assistant-App ist Zielarchitektur, aber noch nicht fertig implementiert. Geplant sind unter anderem:

- konfigurierbare Today-Größe
- Rare-/Long-Gewichtung
- Artist-Min-Gap
- History-Sync-Intervall
- Spotify-/Degraded-Status
- manuelle Aktionen
- tabellarische Today-Anzeige mit Filter- und Sortiermöglichkeiten

Weitere verbindliche Details stehen in [`PROJECT.md`](PROJECT.md).
