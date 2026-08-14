# Development and Release Workflow

This workflow is mandatory for all repository work. It protects `main` as the
stable, approved state and keeps stabilization work focused.

## Source of truth and development environment

GitHub is the authoritative source of truth for this project.

A Windows checkout is optional. It is not a required development, review,
release, or test step unless a task specifically needs Windows-local tooling.
Do not keep Windows synchronized after every merge merely because an older
workflow used it as an intermediate step.

Prefer the shortest safe path:

`worker -> GitHub -> Home Assistant target environment`

When direct target-environment inspection is useful, prefer Home Assistant-side
tools such as Studio Code Server or Advanced SSH & Web Terminal rather than
adding an unnecessary Windows handoff.

## Branch and pull request workflow

Do not make product-code changes directly on `main`. Use this standard flow:

1. Create a worker or feature branch.
2. Implement the scoped change and commit it on that branch.
3. Push the branch and open a pull request targeting `main`.
4. Run tests and CI, complete review, and address findings.
5. Merge the approved pull request.
6. Update/deploy only the affected component to the Home Assistant target.
7. Use the least disruptive reload/restart that is technically sufficient.
8. Perform the defined real-world test.

A local Windows `git pull` is only required when that checkout will actually be
used for subsequent local work.

Direct commits to `main` are permitted only for explicitly justified exception
cases. The justification must be recorded in the pull request, release, or
commit context as appropriate.

## AI and human responsibility

Connected AI tooling should perform available repository operations itself
when safe and technically possible, including branch creation, implementation,
validation, push, PR creation/update, diff inspection, and CI inspection.

Do not ask the human operator to repeat Git or GitHub steps that connected AI
tooling can already perform.

The human operator should normally be involved only for:

- explicit approval of disruptive runtime actions;
- actions for which no trusted Home Assistant connector/API is available;
- browser or physical-device interaction that cannot be automated safely;
- final product judgment during real-world validation.

After each worker task, report only the actual remaining human steps.

## Reload and restart discipline

Restarts are an escalation path, not a routine development step. Always choose
the least disruptive mechanism that is sufficient for the changed component.

Use this order:

1. no restart/reload if the change is already effective;
2. reload or reopen the affected Ingress/browser UI;
3. reload the affected Home Assistant integration/configuration domain when supported;
4. restart only the Playlist Assistant add-on or affected service;
5. restart Home Assistant Core only when technically required;
6. reboot the host only for genuine host-level requirements.

A full Home Assistant restart must not be requested as a precaution. State the
technical reason whenever Core restart or host reboot is required.

Examples:

- Ingress JavaScript/CSS-only change: reload/reopen the UI first.
- Add-on runtime change: update/restart the add-on; do not restart Core unless required.
- Custom Integration change: reload the integration when supported; otherwise restart Core only if necessary.

## Stabilization and release policy

The Custom Integration and Home Assistant add-on have independent versions.
Change only the version of the component whose delivered code changes.

Beta versions must be real-world tested before a final release is created.
During a stabilization or beta phase, do not add product features. Resolve
observed real-world blockers first.

## Public language policy

All public project text must be in English, including release notes, changelog
entries, the README, public documentation, pull request titles and
descriptions, and GitHub and HACS metadata.

## Worker selection

Choose the worker model and reasoning level according to task complexity:

- Use a fast, economical model for small or mechanical changes.
- Use a medium model for normal repository work.
- Use the most expensive, high-reasoning option only for genuinely complex
  architecture work or difficult debugging.

Do not use the most expensive setting by default.

## Required worker handoff

Every worker completion report must state:

- cause or goal;
- changed files;
- version changes;
- tests run and their results;
- commit SHA;
- branch;
- pull request number and URL;
- remaining real-world validation.

The worker should normally create or update the pull request itself and stop
before merge unless explicitly authorized otherwise.

The final handoff must contain only the remaining operator actions, for example:

1. review/approve the PR when human review is still required;
2. merge if not performed through connected tooling;
3. update only the affected Home Assistant component;
4. use the minimum required reload/restart;
5. perform the defined real-world test.

Do not include optional Windows checkout synchronization unless Windows will be
used for subsequent local work.