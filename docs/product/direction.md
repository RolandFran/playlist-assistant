# Playlist Assistant – Produktrichtung

**Status:** verbindliche Produktrichtung

Playlist Assistant ist langfristig nicht nur ein Generator für eine Spotify-Playlist namens `Today`. `Today` ist ein sinnvoller Default und Teil der aktuellen Implementierung, aber nicht die Definition des Produkts.

Das langfristige Ziel ist, Nutzern dabei zu helfen, Musik, von der sie bereits wissen, dass sie ihnen gefällt, tatsächlich wieder zu hören, die Auswahl kontrollierbar zu gestalten und ihre Spotify-Musikumgebung langfristig zu pflegen und zu schützen.

## Zentrales Produktmodell

Das zentrale Objekt ist eine **Selection**: eine konkrete, geordnete Menge von Tracks, die aus Quellen, Hörhistorie, Metadaten und Auswahlregeln erzeugt wird.

Eine Selection ist nicht dasselbe wie ihr Output.

- **Play** spielt die aktuelle Selection direkt über Spotify ab.
- **Save** speichert die aktuelle Selection dauerhaft als Spotify-Playlist.

Eine Spotify-Playlist ist damit ein möglicher Output von Playlist Assistant und nicht die interne Definition einer Selection.

## Profile

Ein Profil beschreibt, wie eine Selection erzeugt werden soll. Profile können später Source-Playlists, Scoring, Genre- oder Mood-Gruppen, Ausschlüsse, Artist-Abstand, Größe und weitere Regeln kombinieren.

Dasselbe Profil kann einmalig oder nach Zeitplan ausgeführt werden. Eine tägliche Selection ist nur eine geplante Ausführung desselben Modells und kein separates Produktkonzept.

## Tagesmodell

Für ein tägliches Profil kann Playlist Assistant einmal pro Tag eine feste Selection erzeugen. Wird sie später erneut abgespielt, soll der noch nicht gehörte Rest verwendet werden. Eine manuelle **New**-Aktion kann die aktuelle Selection bewusst verwerfen und neu erzeugen. Am nächsten geplanten Tag entsteht automatisch die nächste Selection.

Eine permanent nachwachsende Radio-Queue ist dafür nicht notwendig. Die tägliche Neuerzeugung bildet bereits einen begrenzten Rolling-Mechanismus.

## Persönlicher Musikkatalog

Hörhistorie und Relevanz für Playlist Assistant sind getrennte Konzepte.

- Die Hörhistorie kann alle beobachteten Wiedergaben enthalten.
- Ein Track wird für Metadata-Enrichment relevant, sobald er mindestens einmal in einer eingebundenen Source-Playlist vorkam.
- Sobald ein Track relevant geworden ist, dürfen seine angereicherten Metadaten nicht verloren gehen, nur weil die betreffende Playlist später nicht mehr als aktive Source verwendet wird.

Source-Playlists bestimmen die aktuelle Auswahlberechtigung; sie besitzen nicht die Track-Metadaten.

## Produktbereiche

Langfristige Produktbereiche sind unter anderem:

- Entdecken und Wiederentdecken
- Selection und Kontrolle
- Play und Save
- Profile, Genres, Moods und Smart Grouping
- Reparatur nicht verfügbarer oder ersetzter Tracks
- Playlist-Schutz und Backups
- Insights und Hörstatistiken
- Datenqualität und Integrität der Hörhistorie
- Track-Identität, Metadaten und Provenance

Diese Bereiche beschreiben die Richtung. Die aktuelle Entwicklungspriorität bleibt die **Beta-Stabilisierung**.