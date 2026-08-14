# Playlist Assistant AI Instructions

Before implementing repository changes, read:

- `docs/development.md`
- `PROJECT.md`
- relevant product documentation under `docs/`

## Mandatory workflow

- GitHub is the source of truth.
- Do not require or synchronize a Windows checkout unless the task genuinely needs Windows-local tooling.
- Prefer `worker -> GitHub -> Home Assistant target environment`.
- The normal chat/orchestrator prepares the worker plan and obtains explicit user approval before repository implementation begins.
- Once started, the worker executes the approved assignment directly. It must not create another worker plan or wait for another approval unless a new blocker, destructive action, missing capability, or scope-changing risk appears.
- Work only on a dedicated non-`main` branch.
- Before the first repository write, verify the current `main` HEAD read-only, create the dedicated branch from the intended base commit, then verify read-only that the branch points to that commit.
- Every content write must name the intended non-`main` branch explicitly. Never omit the branch argument for create, update, or delete operations.
- Direct content writes to `main` are prohibited. Normal changes reach `main` only through an explicitly approved pull-request merge.
- If any repository write fails, a required capability is missing, or tooling behaves unexpectedly, stop immediately and report the condition. Do not improvise with a different write action or fallback path.
- `main` ref updates, force updates, history rewrites, and other destructive recovery actions require explicit human approval. The only exception is immediate containment of an assistant-caused unexpected mutation when delaying containment would increase risk; in that case contain the incident minimally, then report it immediately and prominently.
- Any unexpected repository mutation or workflow violation must be reported immediately with cause, impact, remediation performed, and the read-only verified final state.
- Implement only the scoped change.
- Run relevant tests and validation.
- Commit and push.
- Open or update the pull request against `main`.
- Do not merge unless explicitly authorized.
- Public repository text must be in English.
- The Custom Integration and add-on have independent versions; change only the affected component version.
- During beta/stabilization, fix observed blockers before adding features.
- Use the least expensive AI model that is sufficient for the task.
- Automate recurring repository, validation, PR, release-preparation, and handoff work whenever it can be done safely and repeatably.
- Minimize operator effort: ask the human only for genuine approval gates, unavailable target-system actions, or real-world product validation.

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
