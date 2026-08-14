# Project Development Notes

The cross-project workflow, repository-safety rules, worker assignment format,
approval gates, model selection, release policy, and completion-report contract
are canonical in the
[AI-assisted development workflow](https://github.com/RolandFran/projects-wiki/blob/main/shared/ai-assisted-development-workflow.md).

This file contains Playlist Assistant-specific technical notes only.

## Component and validation boundaries

The Custom Integration and Home Assistant add-on version independently. Change
only the version of the component whose delivered code changes.

During beta or stabilization, fix observed blockers before adding features.
Validate the changed Python, integration, add-on, or Ingress path at the smallest
relevant scope. Automated checks do not replace required target-environment
validation.

## Home Assistant runtime actions

For Playlist Assistant changes, choose the smallest sufficient action:

1. reload or reopen Ingress for JavaScript/CSS-only changes;
2. reload the Custom Integration when Home Assistant supports it;
3. restart only the Playlist Assistant add-on or affected service;
4. restart Home Assistant Core only when the changed integration/runtime cannot
   be reloaded safely.

Do not restart Home Assistant Core as a precaution. State the technical reason
when it is necessary.

## Protect main ruleset

As verified on 2026-08-14, the active GitHub ruleset **Protect main** applies to
the default branch. It blocks branch deletion and non-fast-forward updates, and
requires pull requests for changes. The ruleset currently requires zero approving
reviews, does not require code-owner review, last-push approval, or review-thread
resolution, and permits merge, squash, and rebase merges.

This is a concise configuration record, not a replacement for the canonical
governance.
