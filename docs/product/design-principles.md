# Playlist Assistant – Designprinzipien

**Status:** verbindliche Produkt- und UX-Prinzipien

## Detaillierte Musikdaten bleiben im Playlist Assistant

Playlist Assistant besitzt die detaillierten Musikdaten, Analysen, Selection-Logik, Source-Beziehungen, Metadata-Enrichment, Klassifikationen und Track-Ansichten.

Home Assistant ist die Steuerungs- und Automatisierungsebene. Dort werden nur bewusst ausgewählte Actions, kompakte Statusinformationen und sinnvolle aggregierte Sensoren bereitgestellt.

Große Track-Datenmengen dürfen nicht als große Anzahl von Home-Assistant-Entities abgebildet werden.

Neue Kennzahlen werden zuerst im Playlist Assistant umgesetzt und bewertet. Erst wenn sich ein konkreter Nutzen für Home-Assistant-Automationen oder Dashboards zeigt, werden daraus Sensoren.

## Selection ist nicht Output

Der Nutzer soll eine konkrete Selection ansehen können und anschließend entscheiden, was mit genau diesem Ergebnis geschieht.

Primäre Output-Aktionen sind:

- **Play** – Selection direkt abspielen.
- **Save** – Selection als Spotify-Playlist speichern.

Play und Save müssen auf derselben Selection arbeiten und dürfen sie nicht unabhängig voneinander neu berechnen.

## Normale UI einfach halten, Analyse optional einblenden

Die primäre Track-Tabelle bleibt kompakt. Zusätzliche Analyseinformationen werden bevorzugt über optionale **Spaltengruppen** eingeblendet und nicht primär über das Aufklappen einzelner Zeilen.

Wer eine analytische Dimension aktiviert, möchte sie normalerweise über die gesamte Tabelle vergleichen. Spaltengruppen sollen deshalb Sortierung und Filterung über alle Tracks unterstützen.

Mögliche Gruppen sind Wiedergabe, Selection, Sources, Track, Metadaten, Audio Features, Klassifikation und Datenqualität.

## Auswahl nachvollziehbar machen

Playlist Assistant soll transparente Selection-Logik bevorzugen. Wo sinnvoll, soll die UI erklären können, warum ein Track ausgewählt wurde, zum Beispiel über Score-Komponenten, Source, Rang und später Metadaten- oder Profilregeln.

## Angereichertes Wissen erhalten

Metadaten gehören zur Track-/Katalogebene und nicht zu einer einzelnen Playlist-Mitgliedschaft. Das Entfernen einer Playlist aus den aktiven Sources darf bereits erworbene Zusatzdaten ehemals relevanter Tracks nicht löschen.

## Externe Metadaten austauschbar halten

Provider-spezifische Daten werden hinter einem provider-unabhängigen Modell normalisiert und behalten, soweit sinnvoll, ihre Herkunft (Provenance). Selection Engine und UI dürfen nicht direkt vom Schema eines einzelnen Providers abhängig sein.

## Stabilität vor Erweiterung

Beta-Stabilisierung hat Vorrang vor neuen Produktfeatures. Die Zukunftsdokumentation soll Architektur-Sackgassen vermeiden und Ideen erhalten, aber den aktuellen Implementierungsumfang nicht vorzeitig erweitern.