# Vereinfachtes tägliches Selection-Modell

**Status:** Idee  
**Priorität:** P1  
**Bereich:** Playback / Scheduling  
**Voraussetzung:** Beta-Stabilität und Direct Playback

## Ziel

Das Tagesmodell soll möglichst einfach bleiben. Ein tägliches Profil erzeugt einmal pro Tag eine feste Selection, zum Beispiel 200 Tracks.

Die Selection bleibt für diesen Tag bestehen und wird nicht nach jedem gehörten Track permanent erweitert.

## Bedienmodell

Für die aktuelle Daily Selection genügen im Kern:

- **Play** – spielt die heute noch nicht gehörten Tracks der aktuellen Selection.
- **New** – verwirft die aktuelle Selection bewusst und erzeugt jetzt eine neue vollständige Selection.
- **Save** – speichert die aktuelle Selection optional als Spotify-Playlist.

Beispiel:

- 04:00: 200 Tracks werden erzeugt.
- 20 davon werden gehört.
- Der Nutzer startet zwischenzeitlich andere Musik in Spotify.
- Er drückt später erneut Play.
- Playlist Assistant verwendet die verbleibenden 180 Tracks derselben Daily Selection.
- Am nächsten Tag wird planmäßig eine neue Selection erzeugt.

## Kein eigener Rolling-Radio-Modus

Ein permanentes Nachfüllen auf immer 200 offene Tracks ist für dieses Tagesmodell nicht erforderlich. Die tägliche Neuerzeugung übernimmt bereits die gewünschte Rotation auf einer klar begrenzten Zeitskala.

## Home Assistant

Als zusätzliche HA-Steuerungen sind insbesondere sinnvoll:

- aktuelle Selection abspielen
- Selection bewusst neu erzeugen

Save ist eher eine Funktion der Playlist-Assistant-Oberfläche, kann später aber bei konkretem Automationsbedarf ebenfalls exponiert werden.

## Offene Fragen

- Wie wird zuverlässig bestimmt, welche Tracks der aktuellen Daily Selection heute bereits gehört wurden?
- Was geschieht bei einer manuellen Neuerzeugung mit der vorherigen Selection – nur ersetzen oder für Diagnose/Verlauf archivieren?

Die Lösung soll möglichst ohne zusätzliche Playback-Session-Komplexität auskommen.