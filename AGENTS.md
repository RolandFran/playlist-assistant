# Playlist Assistant AI Instructions

Before implementing repository changes, read:

- `docs/development.md`
- `PROJECT.md`
- relevant product documentation under `docs/`

## Mandatory workflow

- GitHub is the source of truth.
- Do not require or synchronize a Windows checkout unless the task genuinely needs Windows-local tooling.
- Prefer `worker -> GitHub -> Home Assistant target environment`.
- Work on a dedicated branch.
- Implement only the scoped change.
- Run relevant tests and validation.
- Commit and push.
- Open or update the pull request against `main`.
- Do not merge unless explicitly authorized.
- Public repository text must be in English.
- The Custom Integration and add-on have independent versions; change only the affected component version.
- During beta/stabilization, fix observed blockers before adding features.
- Use the least expensive AI model that is sufficient for the task.

## Restart policy

Do not request a Home Assistant restart by default.
Use the least disruptive sufficient action:

1. no reload/restart;
2. UI/Ingress reload;
3. integration/config reload when supported;
4. add-on/service restart;
5. Home Assistant Core restart only when technically required;
6. host reboot only for genuine host-level requirements.

State the technical reason when a disruptive restart is required.

## Worker handoff

The completion report must include:

- cause/goal;
- changed files;
- version changes;
- tests and results;
- commit SHA;
- branch;
- PR number/URL;
- remaining real-world validation.

Ask the human operator only for steps that connected tooling cannot safely perform.