# ADR-0013: Dependabot owns dependency maintenance

- Status: accepted
- Date: 2026-11-27

## Context

ADR-0001 delegated dependency maintenance to a hosted third-party
app: scheduled, grouped, with graded automerge. Installing that app
on the dedicated organization means the GitHub marketplace flow -
a third-party platform app, its permission grant, and the hosting
vendor's account onboarding. At the owner's arbitration of
2026-11-27 that friction is judged disproportionate for a personal
organization of a handful of repositories. Dependabot is native to
GitHub: no app to install, no account to create, no organization
grant - it runs from a config file committed in the repository, and
it manages uv.lock (the "uv" ecosystem) and GitHub Actions
references.

## Options considered

1. Install the hosted app anyway. Rejected by the owner:
   account and onboarding friction, for an automation whose value
   here is weekly batches.
2. Self-host an update bot in GitHub Actions. Rejected: a PAT secret, a
   scheduled workflow, Actions minutes and a bigger CI surface -
   more moving parts than the job warrants.
3. Manual updates by the human. Rejected: recurring overhead
   against ADR-0001's delegation principle.
4. Dependabot driven by a committed dependabot.yml. Chosen.

## Decision

- `.github/dependabot.yml` ships in the seed; the hosted bot's
  configuration file leaves it.
- Version updates run weekly, grouped into one non-major batch per
  ecosystem (uv, github-actions), and target `daily` - dependency
  pull requests follow the branch model like any other pull request.
- Major updates stay ungrouped: individual pull requests, handled
  per the escalation list.
- Agents never bump dependencies themselves - the bot owns that
  job (ADR-0001, unchanged).
- This supersedes the maintenance clause of ADR-0001. Both stale
  clauses - maintenance, and the release clause ended by ADR-0009
  - are de-staled in ADR-0001 itself: the template may edit its
  ADRs; only instantiated repositories freeze them (owner's
  arbitration of 2026-11-27).

## Consequences

- No platform app to enable at bootstrap: the file is active with
  the push, and ADR-0001's de-staled text now records the same.
- Accepted deltas against the former hosted-app clause, recorded
  here once:
  no per-update-type automerge (patches no longer merge themselves
  on green CI - every Dependabot pull request goes through the
  normal path, CI green then the merge driver); no `needs-human`
  label on majors (Dependabot labels are per-configuration, not
  per-update-type - a major pull request is recognizable by its
  shape: one dependency, a major version jump); Dependabot security
  updates, when enabled in repository settings, target the default
  branch by platform design - version updates target `daily`,
  security updates target `main`.
- Bootstrap honesty: accepted out-of-band, for the same reason as
  ADR-0009 to ADR-0012 - it defines the state the seed ships, and
  the draft window of ADR-0011 does not exist as a process at
  bootstrap time. The window applies to every ADR opened after
  instantiation, from 0014 on.
