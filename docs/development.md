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

## Orchestrator and worker approval boundary

Planning and approval happen before repository implementation starts.

The normal ChatGPT chat acts as the orchestrator: it prepares a concise worker
plan and assignment, then waits for explicit user approval before starting
repository implementation.

Once the worker is started, it executes the approved assignment directly. It
does not create another worker plan or wait for another approval unless it
encounters a new blocker, destructive action, missing capability, or a risk
that would materially change the approved scope.

## Branch and pull request workflow

Direct content changes on `main` are prohibited. Use this standard flow:

1. Read-only verify the current `main` HEAD and record the intended base commit.
2. Create a dedicated worker or feature branch from that exact base.
3. Read-only verify that the new branch points to the intended base commit.
4. Implement the scoped change on that branch only.
5. For every create, update, or delete operation, explicitly provide the
   non-`main` branch. Never rely on a tool default for the target branch.
6. Commit and push the branch and open a pull request targeting `main`.
7. Run tests and CI, complete review, and address findings.
8. Merge only after explicit user approval.
9. Update/deploy only the affected component to the Home Assistant target.
10. Use the least disruptive reload/restart that is technically sufficient.
11. Perform the defined real-world test.

A local Windows `git pull` is only required when that checkout will actually be
used for subsequent local work.

Normal repository changes reach `main` only through an explicitly approved pull
request merge. There is no routine direct-commit exception for `main`.

## Repository write failure and incident handling

A failed write, missing capability, or unexpected tool result is a hard stop.
Do not improvise by switching to another write action, omitting required
arguments, writing to the default branch, moving refs, or using a destructive
fallback.

Before any further repository mutation, report the failure and obtain any new
approval that the changed situation requires.

Direct `main` ref updates, force updates, history rewrites, and other destructive
recovery actions require explicit human approval. The sole containment exception
is an assistant-caused unexpected mutation where delaying containment would
increase risk. In that case, perform only the minimum immediate containment
needed and then report the incident prominently without delay.

Every unexpected repository mutation or workflow violation must be reported
with all of the following:

- root cause;
- affected refs/files and practical impact;
- remediation performed;
- read-only verification of the final repository state.

## AI and human responsibility

Connected AI tooling should perform available repository operations itself
when safe and technically possible, including branch creation, implementation,
validation, push, PR creation/update, diff inspection, and CI inspection.

Recurring repository, validation, pull-request, release-preparation, and handoff
steps should be automated or standardized whenever this can be done safely and
repeatably.

Do not ask the human operator to repeat Git or GitHub steps that connected AI
tooling can already perform.

The human operator should normally be involved only for:

- the explicit approval gate before worker/repository implementation begins;
- explicit approval of destructive repository actions;
- explicit pull-request merge and release approval;
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
