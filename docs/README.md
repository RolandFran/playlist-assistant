# Playlist Assistant – Dokumentation

Dieses Verzeichnis ist die repository-interne Wissensbasis für Playlist Assistant.

## Verbindliche Dokumente

- [`../PROJECT.md`](../PROJECT.md) – aktueller verbindlicher technischer Projektstand; bleibt als technische Projektdokumentation auf Englisch.
- [`docs-design-notes.md`](docs-design-notes.md) – Architecture Decision Log (ADR) mit Begründungen und überholten Entscheidungen; bleibt auf Englisch.
- [`product/direction.md`](product/direction.md) – langfristige Produktrichtung und Produktgrenzen.
- [`product/design-principles.md`](product/design-principles.md) – dauerhafte Produkt-, Daten- und UX-Prinzipien.
- [`ideas/README.md`](ideas/README.md) – priorisierter Zukunfts-Backlog. Alles, was bewusst erst nach dem stabilen Kern umgesetzt werden soll, gehört hierher.

## Operative Dokumentation

- [`development.md`](development.md) – Entwicklungs- und Release-Workflow.
- [`HACS.md`](HACS.md) – HACS-Installation und Distribution.
- [`user-guide.md`](user-guide.md) – Anwenderdokumentation.

## Sprachregel

Die interne Planungs- und Ideen-Wiki unter `docs/product/` und `docs/ideas/` wird auf Deutsch geführt, damit sie leicht gelesen und gepflegt werden kann.

Öffentliche bzw. technische Repository-Dokumentation wie README, HACS-Dokumentation, Releases, PRs, Issues, `PROJECT.md` und ADRs bleibt auf Englisch.

## Dokumentationsregel

Keine konkurrierenden Architektur- oder Backlog-Dokumente an anderen Stellen des Repositories anlegen. Neue Zukunftsideen werden in der passenden Datei unter `docs/ideas/` gepflegt und in `docs/ideas/README.md` einsortiert. Dauerhafte Produktprinzipien gehören unter `docs/product/`. Technische Entscheidungen mit Begründung gehören in den ADR.

Aktuelle Entwicklungspriorität ist die **Beta-Stabilisierung**. Zukunftsideen sind Dokumentation und Backlog, keine Freigabe zur sofortigen Implementierung.