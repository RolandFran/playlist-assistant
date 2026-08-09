# Playlist Assistant – verbindlicher Projektstand

## Ziel
Playlist Assistant erstellt eine dynamische Spotify-Playlist aus definierten Quellplaylists. Kandidaten stammen ausschließlich aus Spotify-Playlists, deren Beschreibung den Marker `#today-source` enthält.

Die tägliche Zielplaylist wird nach einem Score erzeugt. Die Zielgröße ist standardmäßig 200 Titel und später über Home Assistant konfigurierbar.

## Zentrale Datenbank
Datei: `playlist_assistant.db`

Es gibt genau eine produktive SQLite-Datenbank.

### Tabellen
- `source` – aktuell gefundene Spotify-Quellplaylists mit `#today-source`
- `playlist` – aktuelle Tracks dieser Quellplaylists; ein Track kann in mehreren Quellen vorkommen
- `history` – einzelne Spotify-Wiedergaben aus Extended Streaming History und dem laufenden Collector
- `sync_state` – technische Checkpoints des laufenden Collectors

## Datenfluss
1. `sync.py` sucht alle Playlists mit `#today-source` und aktualisiert `source` und `playlist` als Momentaufnahme.
2. `history.py` importiert Spotify Extended Streaming History in `history` (`data_source = 'extended'`).
3. `collector.py` zieht neue Recently-Played-Ereignisse nach (`data_source = 'recent'`) und schreibt Checkpoints nach `sync_state`.
4. `stats.py` wertet Kandidaten aus `playlist` gegen `history` aus.
5. `analyze.py` dient der lesenden Detailanalyse.
6. `scoring.py` berechnet Rare-, Long- und Gesamt-Score und erzeugt daraus die Today-Auswahl.

## Kandidaten
- Kandidaten stammen ausschließlich aus `playlist`.
- Doppelte Tracks aus mehreren Source-Playlists werden über `track_uri` zu einem Kandidaten zusammengeführt.
- Standardgröße der Today-Auswahl: 200 Titel.
- Die Größe ist eine Konfiguration und kein fester Bestandteil des Algorithmus.

## Matching / Song-Identität
- Für die Hörstatistik ist der Song-Schlüssel: normalisierter Titel + normalisierter Interpret.
- Verschiedene Spotify-URIs mit identischem Titel + Interpret werden für Play-Count und letztes Hören zusammengeführt.
- Die Spotify-URI bleibt als technische Referenz erhalten, um den ausgewählten Track später in eine Spotify-Playlist schreiben zu können.
- Für Playlist-Kandidaten zählen Wiedergaben erst ab `added_at`, sofern `added_at` vorhanden ist.
- Live-/Remaster-/Acoustic-Zusätze werden derzeit nicht entfernt; nur Groß-/Kleinschreibung und äußere Leerzeichen werden normalisiert.

## Scoring
### Rare Score
- logarithmisch über `play_count`
- 0 Plays => Rare Score 100
- der höchste aktuelle Play-Count bildet das obere Vergleichsende

### Long-not-played Score
- gehörte Titel: logarithmisch über Tage seit dem letzten relevanten Play
- 0-Play-Titel: neutraler Long-Score 50
- unter gleich bewerteten 0-Play-Titeln dient das Alter seit `added_at` als Tie-Breaker; ältere Einträge werden zuerst berücksichtigt
- damit bleiben nie gehörte Titel hoch priorisiert, verdrängen aber nicht automatisch die gesamte Today-Auswahl

### Combined Score
- Standard: 50 % Rare + 50 % Long
- Gewichte sind konfigurierbar

### Artist-Spacing
- Auswahl erfolgt absteigend nach Combined Score
- Standard: `artist_min_gap = 10`
- derselbe `artist_name` soll damit nicht direkt hintereinander erscheinen
- Artist-Spacing verändert nicht den Score, sondern nur die Reihenfolge/Auswahl
- falls ein konfigurierter Gap mit dem Restpool nicht eingehalten werden kann, darf die Auswahl den Gap ausnahmsweise lockern, damit die Zielgröße erreicht wird

## Lokale Defaults
Derzeit stehen die relevanten Werte zentral in `scoring.py`:

```python
TODAY_SIZE = 200
RARE_WEIGHT = 0.50
LONG_WEIGHT = 0.50
ARTIST_MIN_GAP = 10
```

Diese Konstanten sind nur die lokale Übergangskonfiguration.

## Home-Assistant-Zielarchitektur
Die relevanten Einstellungen sollen später nicht dauerhaft im Python-Code gepflegt werden.

Geplant ist:
- Home Assistant stellt die konfigurierbaren Werte bereit.
- Im Konfigurationsbereich bzw. im Ausgabe-Dashboard werden die Parameter als Bedienelemente angezeigt.
- Im selben Dashboard wird die neu erzeugte Playlist als Tabelle dargestellt.
- Änderungen an Reglern sollen die nächste Playlist-Berechnung beeinflussen, ohne Codeänderung.

Mindestens vorgesehen:
- Playlist-Größe / `today_size`
- Rare-Gewichtung
- Long-Gewichtung
- Artist-Min-Gap

Die Python-Engine soll so bleiben, dass später nur die Herkunft der Konfigurationswerte ausgetauscht wird: lokale Defaults heute, Home-Assistant-Entities später.

## Reports
- `reports/scoring_output.txt` – vollständige Kandidatenliste mit Score, Rare, Long, Plays und Tagen
- `reports/today_output.txt` – aktuell ausgewählte Today-Titel in der durch Artist-Spacing erzeugten Reihenfolge

Die Textreports sind Entwicklungs-/Kontrollausgaben. Langfristig ist die Home-Assistant-Playlist-Tabelle die Benutzeroberfläche.

## Dateiverantwortung
- `client.py` – einfacher Spotify-API-Verbindungs-/Ausgabetest; kein Kernmodul
- `collector.py` – laufender Recently-Played-Collector
- `sync.py` – Source-Playlist- und Kandidaten-Synchronisierung
- `history.py` – einmaliger/wiederholbarer Extended-History-Import
- `stats.py` – Kandidaten-/History-Statistik
- `analyze.py` – Detailanalyse
- `scoring.py` – Scoring und Today-Auswahl
- `tools/migrate_db_names.py` – Legacy-Hilfsskript für alte DB-Namen

## Verbindliche Namensregeln
Nicht mehr verwenden:
- `spotify_history.db`
- `source_playlists`
- `playlist_tracks`
- `plays`
- `history.source`

Stattdessen:
- `playlist_assistant.db`
- `source`
- `playlist`
- `history`
- `history.data_source`
