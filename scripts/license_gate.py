"""License gate over the installed environment (ADR-0008, N2).

Dependency admission is argued evidence, not list membership (N2):
the adding agent states the community-validation case in the pull
request, the reviewer verifies the evidence, and two mechanical
fronts fail closed in CI on every pull request - the vulnerability
audit (pip-audit, already in ci.yml) and this license gate. Every
installed distribution must resolve to a license inside
license-allowlist.txt (the shared allowlist format of docs/gates.md);
a distribution with no license metadata at all fails closed, never
passes silently.

The allowed set is configuration, not constitution: an instance
edits the set in its own repository, and a new dependency with an
off-list license is a pull request that argues both the community
validation and the license exception. Compound SPDX expressions are
evaluated the way they bind: ``OR`` is a choice and passes when one
operand is allowed, ``AND`` multiplies and requires every operand,
``WITH`` carries an exception and binds to the operand before it.
"""

import importlib.metadata
from pathlib import Path
from typing import TYPE_CHECKING

from scripts._shared import (
    EXIT_CODE_CRITERIA_UNMET,
    EXIT_CODE_SUCCESS,
    REPOSITORY_ROOT,
)

if TYPE_CHECKING:
    import argparse

ALLOWLIST_PATH = REPOSITORY_ROOT / "license-allowlist.txt"

# PyPI license classifiers are display names, not SPDX identifiers;
# this table is format normalization, not admission policy - which
# licenses are allowed lives only in license-allowlist.txt (N2).
CLASSIFIER_TO_SPDX = {
    "mit license": "mit",
    "apache software license": "apache-2.0",
    "bsd license": "bsd-3-clause",
    "bsd 2-clause license": "bsd-2-clause",
    "bsd 3-clause license": "bsd-3-clause",
    "isc license": "isc",
    "mozilla public license 2.0 (mpl 2.0)": "mpl-2.0",
    "python software foundation license": "psf-2.0",
    "the unlicense (unlicense)": "unlicense",
}


def load_allowed_licenses(path: Path = ALLOWLIST_PATH) -> frozenset[str]:
    """Read the shared allowlist file.

    Format (docs/gates.md): bare SPDX identifiers, one per line,
    sorted; comment lines start with #, blank lines are ignored.
    """
    allowed = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            allowed.add(entry.casefold())
    return frozenset(allowed)


ALLOWED_LICENSES = load_allowed_licenses()


def split_outside_parentheses(text: str, separator: str) -> list[str] | None:
    """Split ``text`` on ``separator`` at depth zero; None when absent."""
    depth = 0
    parts: list[str] = []
    start = 0
    position = 0
    while position <= len(text) - len(separator):
        character = text[position]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif depth == 0 and text[position : position + len(separator)] == separator:
            parts.append(text[start:position])
            start = position + len(separator)
            position += len(separator)
            continue
        position += 1
    if not parts:
        return None
    parts.append(text[start:])
    return parts


def expression_is_allowed(expression: str) -> bool:
    """Evaluate one SPDX license expression against the allowed set."""
    cleaned = expression.strip()
    or_parts = split_outside_parentheses(cleaned, " OR ")
    if or_parts is not None:
        return any(expression_is_allowed(part) for part in or_parts)
    and_parts = split_outside_parentheses(cleaned, " AND ")
    if and_parts is not None:
        return all(expression_is_allowed(part) for part in and_parts)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        inner = cleaned[1:-1].strip()
        if split_outside_parentheses(inner, " OR ") is not None or (
            split_outside_parentheses(inner, " AND ") is not None
        ):
            return expression_is_allowed(inner)
    with_position = cleaned.find(" WITH ")
    if with_position != -1:
        cleaned = cleaned[:with_position].strip()
    return cleaned.casefold() in ALLOWED_LICENSES


def license_violation(
    *,
    expression: str,
    license_classifiers: tuple[str, ...],
    legacy_license: str,
) -> str | None:
    """Return the blocking evidence, or None when the license is allowed.

    Precedence follows the modern core metadata: the license
    expression decides when present, the license classifiers when
    there is none, the legacy license field last. A distribution
    passing none of the three has no license metadata and fails
    closed.
    """
    if expression:
        return None if expression_is_allowed(expression) else expression
    if license_classifiers:
        normalized = [
            CLASSIFIER_TO_SPDX.get(name.casefold(), name.casefold()) for name in license_classifiers
        ]
        if any(name in ALLOWED_LICENSES for name in normalized):
            return None
        return "; ".join(license_classifiers)
    if legacy_license:
        candidate = legacy_license.casefold()
        candidate = CLASSIFIER_TO_SPDX.get(candidate, candidate)
        return None if candidate in ALLOWED_LICENSES else legacy_license
    return "no license metadata at all"


def distribution_violation(*, distribution: importlib.metadata.Distribution) -> str | None:
    """Extract one distribution's metadata fields, then delegate."""
    metadata = distribution.metadata
    return license_violation(
        expression=metadata.get("License-Expression", ""),
        license_classifiers=tuple(
            classifier.split(" :: ")[-1]
            for classifier in metadata.get_all("Classifier", [])
            if classifier.startswith("License")
        ),
        legacy_license=metadata.get("License", ""),
    )


def scan_offenders() -> list[str]:
    """Scan every installed distribution; return one line per offender."""
    offenders: list[str] = []
    for distribution in importlib.metadata.distributions():
        violation = distribution_violation(distribution=distribution)
        if violation is not None:
            offenders.append(f"{distribution.metadata['Name']} {distribution.version}: {violation}")
    return offenders


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the license-gate subcommand: no option, fail closed."""
    subparser = subparsers.add_parser(
        "license-gate",
        help="Fail on any installed license outside the allowed set (ADR-0008 N2).",
        description=(
            "License gate (ADR-0008 N2): every installed distribution must"
            " resolve to a license inside license-allowlist.txt; anything"
            " off-list - or with no license metadata at all - fails the"
            " gate before review starts."
        ),
    )
    subparser.set_defaults(runner=run)


def run(*, arguments: argparse.Namespace) -> int:
    """Entry point: report offenders; exit 1 as soon as one exists."""
    del arguments  # The gate takes no option, on purpose.
    offenders = scan_offenders()
    for offender in offenders:
        print(f"license gate: {offender} - outside the configured allowed set.")
    if offenders:
        print(
            f"license gate: {len(offenders)} distribution(s) outside the allowed set"
            " (the set lives in license-allowlist.txt, N2: configuration,"
            " not constitution)."
        )
        return EXIT_CODE_CRITERIA_UNMET
    return EXIT_CODE_SUCCESS
