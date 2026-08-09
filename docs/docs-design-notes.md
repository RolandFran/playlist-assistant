# Playlist Assistant – Design Notes / Architecture Decision Log

Status: laufende Planungsphase  
Zweck: Entscheidungen kompakt sammeln, bevor die dauerhafte Projektdokumentation finalisiert wird.

## ADR-001 – Spotify-Zugriff zentral kapseln
**Status:** beschlossen

- Spotipy bleibt vorerst als Spotify-Bibliothek erhalten.
- Spotipy wird nicht direkt aus `sync.py`, `collector.py`, `publish.py` oder anderen Fachmodulen verwendet.
- Sämtliche Spotify-Zugriffe laufen über eine zentrale Client-Schicht (`client.py` bzw. später ggf. Paket `spotify/`).
- Die Client-Schicht kapselt:
  - Authentifizierung / Token-Nutzung
  - API-Limits und Batchgrößen
  - Pagination
  - Request-Zählung
  - Fehlerklassifikation
  - Rate-Limit-/Quota-Behandlung
  - strukturiertes Logging
- Ein späterer Austausch von Spotipy gegen direkte HTTP-Aufrufe soll möglich sein, ohne die Fachmodule umzubauen.
- Ein Spotipy-Ersatz wird nur bei einem konkreten technischen Grund erwogen.

## ADR-002 – Spotify-API-Limits sind interne Implementierungsdetails
**Status:** beschlossen

- API-Limits und Batchgrößen werden zentral im Code gepflegt.
- Sie werden nicht als normale Benutzerkonfiguration gespeichert.
- Eine spätere Developer-/Diagnose-Sektion darf die aktuell verwendeten Werte read-only anzeigen.
- Ziel: Spotify-Änderungen sollen durch ein App-Update korrigiert werden können, ohne dass alte Benutzerwerte einen Fix überschreiben.
- Aktuell relevante Größen werden vor Implementierung jeweils gegen die Spotify-Dokumentation geprüft.

## ADR-003 – Pagination zentralisieren
**Status:** beschlossen

- Fachmodule fordern vollständige logische Datenmengen an und kennen die API-Paginierung nicht.
- Beispiel: `sync.py` fordert die Tracks einer Source an; die Client-Schicht entscheidet, wie viele Seiten dafür nötig sind.
- Das Ende der Pagination wird anhand der API-Antwort (`next`, Cursor, Checkpoint etc.) erkannt.
- Spotify-spezifische Page-Größen dürfen nicht über mehrere Module verteilt werden.

## ADR-004 – Source-Sync bleibt inkrementell
**Status:** beschlossen

- Quellplaylists werden über `#today-source` erkannt.
- Unveränderte Sources werden nicht vollständig neu geladen.
- `snapshot_id` wird zur Änderungserkennung verwendet.
- Neue oder tatsächlich geänderte Sources werden geladen.
- Das Entfernen von `#today-source` entfernt die Source sauber aus der lokalen Datenbasis.
- SQLite wird erst geändert, nachdem alle für den jeweiligen konsistenten Sync benötigten Spotify-Daten erfolgreich geladen wurden.

## ADR-005 – History-Collection bedarfsgesteuert
**Status:** beschlossen

- Kein permanenter 30-/60-Minuten-Collector als Default.
- Recently Played wird unmittelbar vor der Today-Erstellung aktualisiert.
- Zusätzlich gibt es später einen manuellen History-Sync für Diagnose, Test und Einrichtung.
- Die Pagination endet, sobald der bereits bekannte History-Checkpoint erreicht bzw. die zeitliche Lücke geschlossen ist.
- Ein periodischer Collector wird erst ergänzt, wenn eine konkrete Funktion ihn benötigt.

## ADR-006 – Rate Limit und Development-Quota unterscheiden
**Status:** beschlossen

- HTTP 429 wird zentral behandelt.
- `QUOTA_EXCEEDED` wird von einem normalen kurzfristigen Rate Limit unterschieden.
- `Retry-After` wird ausgewertet und respektiert.
- Kleine, sinnvolle Wartezeiten dürfen kontrolliert automatisch wiederholt werden.
- Sehr lange Wartezeiten dürfen keinen Prozess stundenlang blockieren.
- Bei einer langen Sperre wird der aktuelle Spotify-Job kontrolliert beendet.
- Die App selbst bleibt verfügbar.
- Keine inkonsistenten Teiländerungen an der DB.

## ADR-007 – Degraded Mode muss im UI sichtbar sein
**Status:** beschlossen

Wenn Spotify temporär nicht verfügbar ist:

- lokale DB-Auswertung bleibt nutzbar,
- vorhandene Scores/Playlist-Daten bleiben sichtbar,
- Spotify-abhängige Aktionen werden deaktiviert bzw. ausgegraut,
- Grund der Sperre wird angezeigt,
- sofern bekannt wird der frühestmögliche neue Versuch angezeigt,
- das Protokoll enthält die technischen Details.

Beispielstatus:
- `Spotify: OK`
- `Spotify: Rate limited`
- `Spotify: Quota erschöpft`
- `Spotify: verfügbar ab …`

## ADR-008 – Logging und Request-Zählung
**Status:** beschlossen

- Strukturierte Logs gehen auf stdout/stderr und sollen später im nativen Home-Assistant-App-Tab **Protokoll** erscheinen.
- Normale erfolgreiche Abläufe werden kompakt geloggt.
- Detaillierte Einzelrequest-Logs sind über Developer-/Diagnoseoptionen zuschaltbar.
- Spotify-Requests werden zentral gezählt.
- Ein Job-Log soll mindestens enthalten:
  - Jobtyp
  - Start/Ende
  - Anzahl Spotify-Requests
  - Anzahl gelesener/geschriebener Elemente
  - Erfolg/Fehler
  - bei 429: Reason und Retry-After
  - ob die DB verändert wurde

## ADR-009 – Home-Assistant-App als Zielplattform
**Status:** beschlossen

Playlist Assistant soll als Home-Assistant-App laufen.

Supervisor-/App-Funktionen sollen genutzt werden statt sie selbst nachzubauen:
- Starten / Stoppen / Neustarten
- Start bei Home-Assistant-Systemstart
- Watchdog
- automatische Updates
- Seitenleisten-Eintrag / Ingress
- native Tabs für Info, Dokumentation, Konfiguration und Protokoll
- Container-Ressourcenanzeige (CPU/RAM), soweit Supervisor sie bereitstellt
- App-/Container-Hostname, soweit Supervisor ihn bereitstellt

## ADR-010 – Konfigurationsseite: Nutzeroptionen vs. Developer-Diagnose
**Status:** beschlossen

Normale Benutzerkonfiguration:
- Today-Größe
- Rare-/Long-Gewichtung
- Artist-Min-Gap
- spätere Scheduling-/Playlist-Optionen

Developer-/Diagnosebereich:
- Log-Level
- detailliertes Spotify-Request-Logging
- API-Diagnose
- Dry Run
- interne Spotify-Limits read-only

Nicht als Benutzeroption:
- Spotify Page Size
- Spotify Write Batch Size
- interne Retry-Konstanten, sofern kein echter Nutzerfall dafür existiert

## ADR-011 – Zusatz-Caching nur bei echtem Nutzen
**Status:** beschlossen

- Keine zusätzliche ETag-/Cache-Schicht nur aus theoretischer Optimierung.
- Sie wird nur ergänzt, wenn sie nachweislich Requests reduziert oder Code vereinfacht.
- Bestehende Mechanismen wie `snapshot_id` und History-Checkpoint haben Vorrang.

## ADR-012 – Dokumentationsstrategie
**Status:** beschlossen

- Während der laufenden Planungsphase wird dieses Decision Log fortgeführt.
- Die endgültige Doku wird erst konsolidiert, wenn das Grunddesign stabil ist.
- Danach vorgesehen:
  - `README.md`
  - `AGENTS.md`
  - `docs/architecture.md`
  - `docs/spotify-api.md`
  - `docs/database.md`
  - `docs/development.md`
- `AGENTS.md` bleibt kurz und verbindlich; Detailwissen liegt in `docs/`.

## ADR-013 – Arbeitsaufteilung Chat / Hermes / Codex
**Status:** beschlossen

- Planung, Architektur und Diskussion sollen im normalen ChatGPT-Chat stattfinden.
- Codex wird gezielt für konkrete Repository-/Implementierungsarbeit eingesetzt.
- Hermes soll nicht unkontrolliert Codex-/Work-Kontingent für reine Projektorganisation, Kanban-Pflege oder lange Planungsgespräche verbrauchen.
- Bevor Hermes zum zentralen Interface wird, muss die tatsächliche Provider-/Kontingent-Routing-Konfiguration eindeutig geklärt sein.

## Offene Punkte

Diese Punkte sind noch nicht final entschieden und werden später ergänzt:

- genaue Retry-Schwellen für kurzfristige vs. lange 429-Sperren
- persistenter App-Status für Spotify-Sperren / Retry-Zeit
- genaue Scheduling-Logik der Today-Erstellung
- genaue HA-Ingress-/Dashboard-Struktur
- Developer-Diagnoseansicht und Statussensoren
- finale Dateistruktur (`client.py` vs. Paket `spotify/`)
- automatische Tests und Mocking-Strategie


## ADR-014 – Erster Spotify-Client-Refactor
**Status:** umgesetzt als Teststand

- `client.py` ist jetzt die einzige Spotify-/Spotipy-Grenze für `collector.py`, `sync.py` und `publish.py`.
- Spotipy-interne Status-Retries sind deaktiviert (`retries=0`, `status_retries=0`).
- Kurze 429-Sperren werden in der Client-Schicht kontrolliert behandelt.
- Lange 429-Sperren führen zu einem kontrollierten Fehler statt stundenlangem Sleep.
- `QUOTA_EXCEEDED` besitzt eine eigene Exception.
- 5xx-Fehler erhalten wenige kurze Retries.
- Request-Zählung erfolgt zentral.
- Playlist- und Recently-Played-Pagination liegen zentral in `client.py`.
- `publish.py` verwendet kein separates `requests` mehr.
- Alle drei Jobs loggen strukturierte Start-/End-/Fehlerereignisse.
- Live-Test gegen Spotify steht noch aus.


## ADR-015 – Spotify-Playlist-Metadaten zentral normalisieren
**Status:** umgesetzt

- Spotify-/Spotipy-Feldnamen wie `items` vs. das ältere `tracks` werden nur in `client.py` behandelt.
- `client.py` stellt Fachmodulen dafür das interne Feld `item_total` bereit.
- `sync.py` kennt die Spotify-spezifischen Feldnamen nicht mehr.
- Dadurch führen API-/Spotipy-Feldänderungen nicht direkt zu unnötigen Full-Syncs.


## ADR-016 – Recently-Played-Gaps rückwärts schließen
**Status:** umgesetzt als Teststand

- Ein `after=<checkpoint>`-Request liefert maximal 50 Plays und genügt bei größeren Lücken nicht.
- Nach der ersten Seite wird bei Bedarf mit `before=<ältester Zeitpunkt der Seite>` rückwärts paginiert.
- `after` und `before` werden nie gleichzeitig gesendet.
- Es werden nur Plays nach dem gewünschten Checkpoint übernommen.
- Bereits gespeicherte Plays bleiben durch den DB-Primärschlüssel/`INSERT OR IGNORE` unverändert.
- `collector.py --recover-after <ISO-Zeitpunkt>` erlaubt einen gezielten Backfill einer bereits entstandenen Lücke.
- Ein Recovery-Lauf darf den gespeicherten `last_played_at`-Checkpoint niemals rückwärts verschieben.


## ADR-017 – History-Collector: 90-Minuten-Default und Gap-Erkennung
**Status:** beschlossen / Basis umgesetzt

- Das spaetere automatische Polling-Intervall der HA-App hat einen Default von **90 Minuten**.
- Das Intervall ist eine Benutzeroption und soll im HA-App-Dashboard bzw. in der Konfiguration feinjustierbar sein.
- Zielbereich vorlaeufig: 15–180 Minuten.
- Ein Sync unmittelbar vor der Today-Erstellung bleibt zusaetzlich vorgesehen.
- Ein manueller History-Sync bleibt vorgesehen.
- Wenn Spotify exakt eine volle Recently-Played-Seite liefert und der aelteste zurueckgegebene Play noch nach dem gespeicherten Checkpoint liegt, setzt der Collector `gap_possible=true`.
- Eine moegliche History-Luecke wird geloggt und soll spaeter im UI sichtbar sein.
- Vereinzelte kleine Luecken sind tolerierbar; systematische oder grosse Luecken sollen erkennbar sein.
- Das Scheduling selbst wird erst in der HA-App implementiert; `collector.py` fuehrt weiterhin einen einzelnen Sync-Lauf aus.


## ADR-018 – Stale-Result-Sicherung für Today
**Status:** umgesetzt

- `scoring.py` speichert in `today_tracks.json` einen Fingerabdruck des DB-Eingangszustands.
- Der Fingerabdruck berücksichtigt aktive Sources, Source-Snapshots, Playlist-/History-Zähler und History-Checkpoints.
- `publish.py` berechnet vor jedem Dry-Run/Write den aktuellen Fingerabdruck erneut.
- Stimmen die Fingerabdrücke nicht überein, wird Publish vor jedem Spotify-Schreibzugriff abgebrochen.
- Dadurch kann eine nach Source-Sync oder History-Update veraltete `today_tracks.json` nicht versehentlich veröffentlicht werden.
- Die Prüfung basiert auf Zustand, nicht auf Dateizeitstempeln.


## ADR-019 – Track-Matching: Spotify-URI zuerst
**Status:** umgesetzt und mit realem Problemfall verifiziert

- Historische Wiedergaben werden primär über die exakte `track_uri` dem Source-Track zugeordnet.
- Nur wenn es für diese URI keinen Treffer gibt, wird auf normalisierten Titel + Interpret zurückgefallen.
- Grund: Spotify-Metadaten können sich zwischen Playlist-API und Extended Streaming History unterscheiden, obwohl dieselbe Track-ID gemeint ist.
- Verifizierter Fall: `Amour, Mon Cher Amour`
  - Playlist-Interpret: `Hot Club De Norvege, Jon Larsen, Jimmy Rosenberg`
  - History-Interpret: `Hot Club De Norvege`
  - Spotify-URI identisch
  - 26 History-Plays wurden über URI korrekt erkannt.
- Interne Match-Werte bleiben maschinenlesbar (`uri`, `title_artist`, `none`); Reports zeigen lesbare Bezeichnungen (`URI`, `Titel+Interpret`, `kein Match`).

## ADR-020 – Verständliche Diagnosebegriffe
**Status:** umgesetzt

- `Max. Tage seit Play` wird als `Längste Hörpause` ausgegeben.
- `Max. Play-Count` wird als `Höchste Wiedergabezahl` ausgegeben.
- Technische interne Feldnamen bleiben unverändert; nur die Benutzer-/Konsolenausgabe wird verständlicher formuliert.
