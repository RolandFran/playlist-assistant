# Playlist Assistant AI Instructions

Before repository work, read:

- [the canonical cross-project governance](https://github.com/RolandFran/projects-wiki/blob/main/shared/ai-assisted-development-workflow.md)
- `PROJECT.md`
- the relevant product documentation under `docs/`

The canonical governance defines worker assignments, approvals, repository safety,
branch/PR handling, model selection, releases, and completion reports.

## Repository-local guardrails

- Keep changes within the approved task scope and preserve the current product
  architecture in `PROJECT.md`.
- Public repository text is English.
- The Custom Integration and Home Assistant add-on version independently; change
  only the affected component version, and only for a delivered component change.
- During beta or stabilization, resolve observed blockers before adding features.
- Follow the project-specific technical and validation notes in
  `docs/development.md`.
