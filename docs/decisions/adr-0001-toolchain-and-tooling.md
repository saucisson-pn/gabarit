# ADR-0001: Toolchain and repository tooling

- Status: accepted
- Date: 2026-11-02

## Context

Each instance of this template picks its own language; the template
itself must not hard-code one. Agents install dependencies dozens of
times per day: any environment drift produces phantom failures that
cost review cycles. Old tool versions carry known bugs; exotic tools
carry an unfamiliarity tax every future reader (human or agent) pays.
The repository must also not rot while agents develop autonomously:
dependency maintenance and release management are pure human overhead
yet are escalation-list decisions - the answer is delegation with
graded oversight. Finally, the drivers (review, merge, night loop)
must be code, not prose: documentation verifies nothing, and the
runtime permission profile allowlists precisely because they are code.

## Decision

- The instance uses the **latest stable version** of its language and of
  every tool in the chain; package management, running and building go
  through the community's de facto standard tools, one tool per job.
- The dependency lockfile is **committed**; environments install only
  through the lockfile - agents never improvise installs.
- For the Python code shipped here: uv (sync/run/lock), hatchling
  (build), Ruff, mypy, pytest, structlog, import-linter.
- **Dependabot** (weekly, grouped non-major batches toward `daily`;
  majors are individual pull requests for the escalation list)
  owns dependency maintenance (ADR-0013). There is no release
  machinery (ADR-0009).
- `tools/` holds the long-lived utilities (the `notify` tool is the
  worked example), each self-contained; the template ships **no product
  code** - an instance's product is created per instance, in the
  language's conventional layout, under the same rules. A new
  top-level directory is an ADR-worthy decision.
- The drivers are **one CLI package**: `scripts/` is a package, each
  driver one subcommand of `python -m scripts`, mirroring the make
  targets one-to-one - `make` stays THE agent surface. Shared plumbing
  lives once (`scripts/_shared.py`, stdlib-only so the git-only
  subcommands run in the barest image; the GitHub transport is the
  `gh` CLI called over subprocess). One exit-code contract: 0 success, 1 criteria
  unmet (nothing written), 2 protocol failure.

## Consequences

- Fast, identical environments everywhere; every daily command is
  documented by the community, not by this repository.
- The project stays current without human busywork; the human sees
  dependency updates as weekly pull requests, and major bumps reach
  the escalation list.
- A new driver verb is one subcommand on the existing CLI - a module, a
  `register`, a make recipe - instead of an eleventh look-alike file.
- Negative: the community's standard changes over time; agents must
  call `python -m scripts <command>` (or the make target), never a
  flat script path.
