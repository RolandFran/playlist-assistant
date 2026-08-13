# Development and Release Workflow

This workflow is mandatory for all repository work. It protects `main` as the
stable, approved state and keeps stabilization work focused.

## Branch and pull request workflow

Do not make product-code changes directly on `main`. Use this standard flow:

1. Create a worker or feature branch.
2. Implement the scoped change and commit it on that branch.
3. Open a pull request targeting `main`.
4. Run tests and CI, complete review, and address findings.
5. Merge the approved pull request.
6. Update the local `main` branch.
7. Prepare the applicable version and release.
8. Perform a real-world test.

Direct commits to `main` are permitted only for explicitly justified exception
cases. The justification must be recorded in the pull request, release, or
commit context as appropriate.

## Stabilization and release policy

The Custom Integration and Home Assistant add-on have independent versions.
Change only the version of the component whose delivered code changes.

Beta versions must be real-world tested before a final release is created.
During a stabilization or beta phase, do not add product features. Resolve
observed real-world blockers first.

Restart Home Assistant only when it is technically required for the change or
the real-world test.

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
- readiness for a pull request or release.

The report must end with a concrete human follow-up sequence:

1. Open or review the pull request.
2. Merge it.
3. Pull the updated `main` branch locally.
4. Create the release or update.
5. Perform the real-world test.
