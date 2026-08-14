# Zukunftsideen – priorisierter Backlog

Dieses Verzeichnis ist der zentrale Pool für alles, was bewusst noch nicht umgesetzt wird.

**Aktuelle Entwicklungspriorität: Beta-Stabilisierung.** Keine der folgenden Ideen soll diese Arbeit unterbrechen, außer sie wird zur Behebung eines konkreten Blockers oder einer erkannten Architektur-Sackgasse notwendig.

Die Priorität beschreibt die vorgesehene Reihenfolge der Prüfung nach einer stabilen Beta. Sie ist keine Release-Zusage. Der Backlog darf bei neuen Erkenntnissen neu priorisiert werden.

## P1 – erste Kandidaten nach Beta-Stabilisierung

1. [Direktes Abspielen und Play/Save](playback/direct-playback.md)
2. [Vereinfachtes tägliches Selection-Modell](playback/daily-selection.md)
3. [Erweiterte Analyse-Tabelle mit Spaltengruppen](analysis/extended-track-table.md)
4. [Metadata Provider und Track-Enrichment](metadata/metadata-providers.md)

## P2 – baut auf der P1-Grundlage auf

5. [Selection-Profile und erweiterte Steuerung](selection/profiles-and-controls.md)
6. [Genres, Mood-Gruppen und Smart Grouping](classification/genres-moods-smart-groups.md)
7. [Audio Features und Sonic Analysis](metadata/audio-features.md)
8. [Insights und Statistiken](analysis/insights-and-statistics.md)

## P3 – spätere Produktbereiche

9. [Lost Tracks: Reparatur und Ersatz](repair/lost-track-repair.md)
10. [Playlist-Backup und Schutz](protect/playlist-backup.md)
11. [History-Integrität und Datenqualität](data-quality/history-integrity.md)
12. [Mehrere Accounts und Capability Handling](accounts/multiple-accounts.md)

## Pflege-Regel

Jede dauerhafte Zukunftsidee bekommt genau eine kanonische Datei in diesem Verzeichnisbaum. Weitere Gespräche zu derselben Idee aktualisieren diese Datei, statt parallele Notizen anzulegen.

Jede Idea-Datei enthält mindestens Status, Priorität, Bereich, Ziel/Nutzen, bisher bestätigte Leitlinien und offene Fragen. Noch nicht entschiedene Details werden ausdrücklich als offen gekennzeichnet und nicht als Beschluss dargestellt.

Wird eine Idee implementiert, wird ihr Status aktualisiert. Das danach tatsächlich gültige Verhalten wird zusätzlich in `PROJECT.md` und – bei einer technischen Architekturentscheidung – im ADR dokumentiert.

`docs/future-features.md` bleibt während der Migration als Legacy-Verweis bestehen, damit alte Referenzen nicht still brechen. Neue Zukunftsideen werden dort nicht mehr gepflegt.