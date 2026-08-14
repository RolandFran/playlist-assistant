# Playlist Assistant Documentation

This directory is the repository-local knowledge base for Playlist Assistant.

## Authoritative documents

- [`../PROJECT.md`](../PROJECT.md) — current authoritative technical project state.
- [`docs-design-notes.md`](docs-design-notes.md) — Architecture Decision Log (ADR), including rationale and superseded decisions.
- [`product/direction.md`](product/direction.md) — long-lived product direction and product boundaries.
- [`product/design-principles.md`](product/design-principles.md) — durable design and UX principles.
- [`ideas/README.md`](ideas/README.md) — prioritized future backlog. Everything intentionally deferred beyond the current stable scope belongs here.

## Operational documentation

- [`development.md`](development.md) — development and release workflow.
- [`HACS.md`](HACS.md) — HACS installation and distribution notes.
- [`user-guide.md`](user-guide.md) — user-facing guidance.

## Documentation rule

Do not create competing architecture or backlog documents elsewhere in the repository. New future ideas should be added to the appropriate file below `docs/ideas/` and indexed in `docs/ideas/README.md`. Durable product principles belong under `docs/product/`. Technical decisions with rationale belong in the ADR.

The current development priority is Beta stabilization. Future ideas are documentation, not authorization to start implementation.