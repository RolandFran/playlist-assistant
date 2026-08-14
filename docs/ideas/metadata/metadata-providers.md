# Metadata Provider und Track-Enrichment

**Status:** Idee  
**Priorität:** P1  
**Bereich:** Metadaten / Datenmodell  
**Voraussetzung:** Beta-Stabilität

## Ziel

Relevante Tracks sollen mit zusätzlichen Informationen angereichert werden können, die Spotify nicht oder nicht mehr zuverlässig über die Web API liefert. Denkbare Quellen sind unter anderem MusicBrainz, TheAudioDB oder später weitere Provider.

## Relevanzregel

Die Regel soll bewusst einfach bleiben:

> Ein Track ist für Enrichment relevant, sobald er mindestens einmal in einer eingebundenen Source-Playlist vorkam.

Tracks, die lediglich in der Hörhistorie vorkommen, aber nie Bestandteil einer Source-Playlist waren, werden nicht allein deshalb angereichert.

Damit vermeiden wir unnötige Provider-Abfragen für Musik, die eventuell nur einmal probeweise gehört wurde.

## Daten bleiben erhalten

Wurde ein Track einmal relevant und angereichert, bleiben diese Daten erhalten, auch wenn die Playlist später aus den aktiven Sources entfernt wird oder der Track dort nicht mehr enthalten ist.

Hörhistorie, Track-Katalog und aktuelle Selection Eligibility sind getrennte Konzepte.

## Provider-unabhängiges Modell

Die internen Datenfelder sollen nicht direkt an das Schema eines Providers gekoppelt werden. Wo sinnvoll, wird zusätzlich die Herkunft gespeichert, zum Beispiel:

- Wert
- Provider
- Zeitpunkt der Abfrage
- Match Confidence
- externe Recording-/Track-ID

Damit können später Provider ergänzt oder ausgetauscht werden, ohne Selection Engine und UI neu zu entwerfen.

## Matching

Für das Matching kommen je nach Provider insbesondere Spotify Track ID, ISRC, Artist, Titel, Album und MusicBrainz Recording Identity in Frage.

Unsichere Matches dürfen nicht still als sichere Wahrheit gespeichert werden. Die konkrete Confidence-/Fallback-Strategie wird erst bei der Implementierung festgelegt.

## Caching

Enrichment-Ergebnisse werden lokal gespeichert. Ein bereits bekannter Track soll bei erneuter Aufnahme in eine Source nicht unnötig komplett neu abgefragt werden. Eine spätere Refresh-Strategie kann veraltete Daten gezielt aktualisieren.

## Beziehung zur UI

Provider-Daten erscheinen später als zusätzliche Spaltengruppen in der Analyse-Tabelle, beispielsweise Metadaten, Audio Features, Klassifikation und Datenqualität.