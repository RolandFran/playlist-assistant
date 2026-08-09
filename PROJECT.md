# Playlist Assistant – verbindlicher Projektstand

## Zweck dieser Datei

`PROJECT.md` beschreibt den **aktuellen verbindlichen Projektstand** und die derzeit gültige Zielarchitektur.

Historische Entscheidungen und Begründungen werden separat in `docs/docs-design-notes.md` als Architecture Decision Log (ADR) geführt. Ältere ADRs können durch spätere ADRs ersetzt sein und sind deshalb nicht automatisch der aktuelle Soll-Zustand.

## Ziel

Playlist Assistant erstellt eine dynamische Spotify-Zielplaylist aus definierten Quellplaylists.

Kandidaten stammen ausschließlich aus Spotify-Playlists, deren Beschreibung den Marker `#today-source` enthält.

Die Today-Auswahl wird anhand eines Scores erzeugt. Die Standardgröße beträgt 200 Titel und soll später über die Home-Assistant-App konfigurierbar sein.

Die von Playlist Assistant verwaltete Spotify-Zielplaylist `Today` ist privat.

## Zielplattform

Playlist Assistant soll als **Home-Assistant-App** betrieben werden.

Die App soll Home-Assistant-/Supervisor-Funktionen nutzen, insbesondere:
- Starten / Stoppen / Neustarten
- Start mit dem Home-Assistant-System
- Watchdog
- App-Updates
- Seitenleisten-Eintrag / Ingress
- native Bereiche für Info, Dokumentation, Konfiguration und Protokoll
- Supervisor-Ressourceninformationen, soweit verfügbar

Die Playlist-Engine bleibt logisch vom bestehenden Home-Assistant-System getrennt. Bestehende HA-Konfigurationen, Integrationen und Node-RED-Flows sollen für die Grundfunktion nicht verändert werden müssen.

## Zentrale Datenbank

Datei: `playlist_assistant.db`

Es gibt genau eine produktive SQLite-Datenbank.

### Tabellen
- `source` – aktuell gefundene Spotify-Quellplaylists mit `#today-source`
- `playlist` – aktuelle Tracks dieser Quellplaylists; ein Track kann in mehreren Quellen vorkommen
- `history` – einzelne Spotify-Wiedergaben aus Extended Streaming History und dem laufenden Collector
- `sync_state` – technische Checkpoints des Collectors

## Aktueller Datenfluss

1. `collector.py` aktualisiert Spotify Recently Played und schreibt neue Wiedergaben nach `history` sowie Checkpoints nach `sync_state`.
2. `sync.py` sucht Playlists mit `#today-source` und aktualisiert `source` und `playlist` inkrementell.
3. `scoring.py` wertet die Kandidaten aus `playlist` gegen `history` aus, berechnet Scores und erzeugt die Today-Auswahl.
4. `publish.py` prüft die Frische des Scoring-Ergebnisses und veröffentlicht die Auswahl bei Spotify.
5. `run.py` ist der zentrale CLI-Einstiegspunkt und kann die komplette Today-Pipeline in fester Reihenfolge ausführen: History → Sources → Scoring → Publish.

Diagnose-/Analysewerkzeuge liegen unter `tools/`, darunter insbesondere `tools/stats.py` und `tools/analyze.py`.

Der Import der Spotify Extended Streaming History ist ein lokaler Einrichtungs-/Importvorgang und liegt bewusst außerhalb des Git-Repositories unter `import/`.

## Spotify-Zugriff

`client.py` ist die zentrale Spotify-/Spotipy-Grenze für die Fachmodule.

Die Client-Schicht kapselt insbesondere:
- Authentifizierung / Token-Nutzung
- API-Aufrufe
- Pagination
- Spotify-Batchgrößen
- Request-Zählung
- Fehlerklassifikation
- Rate-Limit-/Quota-Behandlung
- Logging

Spotify-spezifische API-Limits sind interne Implementierungsdetails und keine normale Benutzerkonfiguration.

## Source-Sync

- Quellplaylists werden über `#today-source` erkannt.
- `snapshot_id` dient zur Änderungserkennung.
- Unveränderte Sources werden nicht vollständig neu geladen.
- Neue oder tatsächlich geänderte Sources werden synchronisiert.
- Wird `#today-source` entfernt, wird die Source aus der lokalen Datenbasis entfernt.
- Die Datenbank wird erst geändert, nachdem die für einen konsistenten Sync nötigen Spotify-Daten erfolgreich geladen wurden.

## Kandidaten und Song-Identität

Kandidaten stammen ausschließlich aus `playlist`.

Für die Bildung eines logischen Song-Kandidaten wird derzeit verwendet:
- normalisierter Titel
- normalisierter Interpret

Mehrere Playlist-Einträge mit demselben normalisierten Titel + Interpret werden als ein logischer Kandidat behandelt. Eine Spotify-URI bleibt als technische Referenz erhalten, um den ausgewählten Track später veröffentlichen zu können.

Normalisierung umfasst derzeit nur:
- Groß-/Kleinschreibung
- äußere Leerzeichen

Live-/Remaster-/Acoustic-Zusätze werden nicht entfernt.

## Matching gegen die Hörhistorie

Historische Wiedergaben werden in dieser Reihenfolge zugeordnet:

1. **Primär:** exakte Spotify-`track_uri`
2. **Fallback:** normalisierter Titel + normalisierter Interpret

Der URI-Match hat Vorrang, weil Spotify-Metadaten zwischen Playlist-API und Extended Streaming History voneinander abweichen können, obwohl dieselbe Spotify-Track-ID gemeint ist.

Für Playlist-Kandidaten werden Wiedergaben erst ab `added_at` berücksichtigt, sofern `added_at` vorhanden ist.

Interne Match-Typen:
- `uri`
- `title_artist`
- `none`

## Scoring

Alle sichtbaren Scores werden auf einer Skala von **0 bis 100** dargestellt.

### Rare Score
- logarithmisch über `play_count`
- 0 Plays → Rare Score 100
- die höchste aktuelle Wiedergabezahl bildet das obere Vergleichsende

### Long-not-played Score
- gehörte Titel: logarithmisch über die Tage seit dem letzten relevanten Play
- 0-Play-Titel: neutraler Long-Score 50
- unter gleich bewerteten 0-Play-Titeln dient das Alter seit `added_at` als Tie-Breaker; ältere Einträge werden zuerst berücksichtigt
- nie gehörte Titel bleiben dadurch hoch priorisiert, verdrängen aber nicht automatisch die gesamte Today-Auswahl

### Combined Score

Standardgewichtung:
- Rare: 50
- Long: 50

Die **Benutzer-/Konfigurationsskala für Gewichtungen ist 1 bis 100**.

Für die mathematische Berechnung dürfen die Werte intern auf Faktoren im Bereich 0.0 bis 1.0 normalisiert werden. Diese interne Darstellung ist kein Benutzerwert.

Rare und Long sollen zusammen 100 ergeben. Wie die spätere UI die Kopplung der beiden Werte umsetzt, wird bei der HA-App-Implementierung festgelegt.

## Artist-Spacing

Standard: `artist_min_gap = 10`

Bei der Auswahl soll derselbe normalisierte Künstler möglichst nicht innerhalb der letzten 10 bereits ausgewählten Positionen erneut vorkommen.

Artist-Spacing verändert nicht den Score, sondern die Reihenfolge bzw. Auswahl.

Wenn der konfigurierte Abstand mit dem verbleibenden Kandidatenpool nicht eingehalten werden kann, darf der Gap ausnahmsweise gelockert werden, damit die konfigurierte Zielgröße erreicht wird.

## Aktuelle lokale Defaults

Die aktuell vorgesehenen Benutzerwerte sind:

```text
TODAY_SIZE = 200
RARE_WEIGHT = 50
LONG_WEIGHT = 50
ARTIST_MIN_GAP = 10
```

Im aktuellen Code liegen die Gewichtungsfaktoren noch als `0.50 / 0.50` in `scoring.py`. Das ist ein Übergangsstand und soll durch eine zentrale Konfigurationsschicht ersetzt werden.

## History-Synchronisierung

`collector.py` führt jeweils einen einzelnen Sync-Lauf aus.

Für die spätere Home-Assistant-App ist derzeit vorgesehen:
- automatisches History-Polling standardmäßig alle **90 Minuten**
- vorläufig konfigurierbarer Bereich: 15–180 Minuten
- zusätzlicher History-Sync unmittelbar vor der Today-Erstellung
- manueller History-Sync für Diagnose, Test und Einrichtung

Eine mögliche History-Lücke soll erkannt und später im UI sichtbar gemacht werden.

## Publish und Stale-Result-Sicherung

`scoring.py` speichert in `reports/today_tracks.json` einen Fingerabdruck des verwendeten DB-Eingangszustands.

`publish.py` berechnet vor Dry-Run bzw. Write den aktuellen Fingerabdruck erneut.

Wenn sich Sources oder History seit dem Scoring verändert haben, wird Publish abgebrochen. Dadurch kann eine veraltete Today-Auswahl nicht versehentlich veröffentlicht werden.

Die Zielplaylist wird privat erstellt bzw. auf privat gesetzt.

## Rate Limits und Degraded Mode

Spotify-Fehler werden zentral über `client.py` behandelt.

Insbesondere:
- HTTP 429 wird kontrolliert behandelt.
- `QUOTA_EXCEEDED` wird von einem normalen kurzfristigen Rate Limit unterschieden.
- `Retry-After` wird ausgewertet.
- kurze sinnvolle Wartezeiten dürfen kontrolliert wiederholt werden.
- lange Sperren dürfen den Prozess nicht stundenlang blockieren.
- bei langen Sperren wird der jeweilige Spotify-Job kontrolliert beendet.
- inkonsistente DB-Teiländerungen sollen vermieden werden.

Für die HA-App ist ein sichtbarer Degraded Mode vorgesehen. Lokale DB-Auswertung und bereits vorhandene Ergebnisse sollen dabei weiterhin nutzbar bleiben, während Spotify-abhängige Aktionen deaktiviert oder als nicht verfügbar markiert werden.

## Konfiguration in Home Assistant

Normale Benutzerkonfiguration soll mindestens umfassen:
- Today-Größe / `today_size`
- Rare-Gewichtung
- Long-Gewichtung
- Artist-Min-Gap
- History-Sync-Intervall
- spätere Scheduling-/Playlist-Optionen

Die Python-Engine soll ihre Laufzeitwerte über eine zentrale Konfigurationsschicht beziehen.

Heute liefert diese Schicht lokale Defaults; später liefert die Home-Assistant-App die konfigurierten Werte.

Noch **nicht verbindlich entschieden** ist, ob einzelne Werte technisch über HA-Entities, App-Konfiguration, interne App-API oder eine Kombination bereitgestellt werden.

## UI-Ziel

Die Home-Assistant-Oberfläche soll später mindestens bieten:
- verständliche Einstellmöglichkeiten für die relevanten Parameter
- Anzeige des Spotify-/Degraded-Status
- manuelle Aktionen wie History-Sync bzw. Today-Erstellung
- die erzeugte Today-Playlist als gut lesbare Tabelle
- Filter- und Sortiermöglichkeiten für die Playlist-Tabelle
- Developer-/Diagnoseinformationen getrennt von normalen Nutzeroptionen

## Reports

Aktuelle Entwicklungs-/Kontrollausgaben:
- `reports/scoring_output.txt` – vollständige Kandidatenliste mit Score, Rare, Long, Plays und Tagen
- `reports/today_output.txt` – aktuell ausgewählte Today-Titel in der durch Artist-Spacing erzeugten Reihenfolge
- `reports/today_tracks.json` – strukturierte Today-Daten für Publish und spätere Weiterverarbeitung

Verständliche Diagnosebegriffe:
- `Höchste Wiedergabezahl`
- `Längste Hörpause`

Die Textreports sind Entwicklungs-/Kontrollausgaben. Langfristig ist die Home-Assistant-Oberfläche die primäre Benutzeroberfläche.

## Dateiverantwortung

- `client.py` – zentrale Spotify-/Spotipy-Grenze
- `collector.py` – einzelner Recently-Played-Sync-Lauf
- `sync.py` – Source-Playlist- und Kandidaten-Synchronisierung
- `scoring.py` – Matching, Scoring und Today-Auswahl
- `publish.py` – Frischeprüfung und Spotify-Publish
- `run.py` – zentraler CLI-Einstiegspunkt / Today-Pipeline
- `db_state.py` – DB-Eingangszustand und Fingerprint für Stale-Result-Sicherung
- `tools/` – Diagnose-, Analyse- und Migrationswerkzeuge
- `docs/docs-design-notes.md` – Architecture Decision Log / Entscheidungsverlauf

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

## Noch offene Architekturpunkte

- genaue Retry-Schwellen für kurzfristige vs. lange 429-Sperren
- persistenter App-Status für Spotify-Sperren / Retry-Zeit
- genaue Scheduling-Logik der Today-Erstellung
- genaue HA-Ingress-/Dashboard-Struktur
- Developer-Diagnoseansicht und Statussensoren
- finale Spotify-Client-Dateistruktur (`client.py` vs. Paket `spotify/`)
- automatische Tests und Mocking-Strategie
- technische Bereitstellung der App-Konfigurationswerte an die Python-Engine

## Arbeitsweise für Repository-Änderungen

- Planung, Architektur und Review erfolgen primär im normalen Chat.
- Codex/Work wird gezielt für klar abgegrenzte Repository-/Implementierungsarbeit eingesetzt.
- Git ist die verbindliche technische Referenz zwischen Chat und Work.
- Größere Änderungen sollen auf einem eigenen Branch bzw. als Pull Request erfolgen.
- Hermes ist für dieses Projekt derzeit kein notwendiger Zwischenschritt und soll nicht ohne konkreten Mehrwert zusätzlichen Work-/Codex-Verbrauch erzeugen.
