# Selection-Profile und erweiterte Steuerung

**Status:** Idee  
**Priorität:** P2  
**Bereich:** Selection / Control  
**Voraussetzung:** Beta-Stabilität und generalisierte Selection

## Ziel

Statt nur einer fest verdrahteten `Today`-Konfiguration sollen später mehrere Profile definieren können, wie eine Selection erzeugt wird.

Ein Profil beschreibt Regeln; eine Selection ist das konkrete Ergebnis dieser Regeln.

## Mögliche Profilparameter

- Source-Playlists
- Selection-Größe
- Rare-/Long-Gewichtung
- Artist Minimum Gap
- Genres oder Gruppen
- Ausschlüsse
- Source-Gewichte
- Track-/Artist-Cooldowns
- Never-played-Priorität
- später weitere Metadata-/Audio-Feature-Regeln

## Einmalig oder geplant

Dasselbe Profil soll grundsätzlich einmalig oder regelmäßig ausgeführt werden können. `Today` wird damit langfristig zu einem sinnvollen Default-Profil bzw. einer Default-Ausführung und nicht zu einer Sonderarchitektur.

## Play und Save

Jede erzeugte Selection kann anschließend direkt abgespielt oder als Spotify-Playlist gespeichert werden. Diese Output-Entscheidung gehört nicht in die Profildefinition selbst.

## Weitere Kontrollideen

Später denkbar:

- Track für den nächsten Lauf pinnen
- Track dauerhaft/regelmäßig pinnen
- einzelne Tracks explizit ausschließen
- einzelne Artists ausschließen
- Regeln pro Profil statt global definieren

Die genaue UI und das endgültige Profil-Datenmodell bleiben offen, bis die Kernfunktionen stabil sind.