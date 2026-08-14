# History-Integrität und Datenqualität

**Status:** Idee / technische Grundlage teilweise vorhanden  
**Priorität:** P3  
**Bereich:** Data Quality  
**Voraussetzung:** stabile History-Synchronisation

## Ziel

Mögliche Lücken in der laufenden Erfassung der Spotify-Hörhistorie sollen erkennbar und nachvollziehbar sein.

Eine normale Zeitspanne ohne Musikwiedergabe ist **keine** Datenlücke.

## Beispiel für eine mögliche Lücke

Letzter bekannter Play: 10:00. Ein späterer Poll liefert das API-Maximum an Einträgen, aber der älteste zurückgelieferte Track stammt bereits von 10:35. Dann fehlt die Überlappung zum bekannten Checkpoint und es kann eine Collection Gap existieren.

## Bereits vorhandene Grundlage

Der History-Poll-Audit speichert technische Informationen zu Polls, darunter vorherigen Checkpoint, Anzahl, ältesten/neuesten Track, Seiten und Coverage-Status. Diese Daten können später die Grundlage für eine sichtbare History-Health-Funktion bilden.

## Spätere Funktionen

- offene mögliche Collection Gaps anzeigen
- Zustände `open`, `accepted`, `resolved`
- eine bekannte Lücke bewusst akzeptieren/ignorieren
- akzeptierte Lücken nicht ständig erneut als neuen Fehler melden
- nach History-Import oder nachträglich ergänzten Daten erneut prüfen
- abgedeckten Zeitraum und Anzahl der Plays transparent darstellen

Die Funktion dient der Datenqualität und soll nicht aus kurzen oder normalen Hörpausen Fehlalarme erzeugen.