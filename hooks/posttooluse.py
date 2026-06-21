#!/usr/bin/env python3
"""blindfold PostToolUse hook.

Fires whenever the agent writes or edits a test file. Scans the expected values
in that file for unjustified or confessed assertions and feeds the verdict back
to the agent — no human runs anything.

This is what makes the discipline *internal*: the agent cannot commit a magic
value without being told to justify it or find the real intended value.

Contract (Claude Code / Codex PostToolUse):
  - stdin: JSON with tool_name and tool_input.file_path
  - exit 0: silent (file not a test, or all assertions are clean / trivial)
  - exit 2: stderr surfaced to agent (unjustified or confessed values found)

Fail behaviour: if the file is ungradeable, exit 2 (fail-closed). Better to
ask the agent to verify manually than silently pass a potentially dishonest test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

TEST_HINTS = ("test", "spec", "__tests__")


def _read_event() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def _file_path(event: dict) -> str | None:
    ti = event.get("tool_input") or {}
    return ti.get("file_path") or ti.get("path") or ti.get("filePath")


def _looks_like_test(path: Path) -> bool:
    posix = path.as_posix().lower()
    return any(h in posix for h in TEST_HINTS)


def main() -> int:
    event = _read_event()
    fp = _file_path(event)
    if not fp:
        return 0

    path = Path(fp)
    if not path.exists():
        return 0

    try:
        import blindfold
    except Exception:
        return 0  # skill not fully installed — don't break the agent

    if path.suffix.lower() not in blindfold.EXT_TO_LANG:
        return 0
    if not _looks_like_test(path):
        return 0

    # Skip intentional fixture / sample files — they may contain confessed values by design.
    posix = path.as_posix().lower()
    if any(part in posix for part in ("/fixtures/", "/testdata/", "/__fixtures__/")):
        return 0
    try:
        if "blindfold: ignore" in path.read_text(encoding="utf-8", errors="replace"):
            return 0
    except OSError:
        return 0

    try:
        result = blindfold.scan_file(path)
    except Exception as exc:
        print(
            f"blindfold: could not scan {path.name} ({exc}); "
            f"verify expected values manually before committing.",
            file=sys.stderr,
        )
        return 2

    if result is None or not result.findings:
        return 0

    unjustified = [f for f in result.findings if f.status == "unjustified"]
    confessed = [f for f in result.findings if f.status == "confessed"]

    if not unjustified and not confessed:
        return 0  # everything is justified or trivial

    lines: list[str] = []

    if confessed:
        lines.append(
            f"blindfold: {path.name} — {len(confessed)} CONFESSED assertion(s) "
            f"(expected value taken from the code's own output):"
        )
        for f in confessed:
            lines.append(f"  L{f.line} [{f.source}]: {f.snippet}")
        lines.append(
            "  A confessed test is a photograph of current behaviour, not a test of "
            "correct behaviour. Find the intended value from spec/doc/math/golden/… "
            "and assert that — not what the code returned."
        )

    if unjustified:
        if lines:
            lines.append("")
        lines.append(
            f"blindfold: {path.name} — {len(unjustified)} UNJUSTIFIED assertion(s) "
            f"(non-trivial literal with no declared source):"
        )
        for f in unjustified:
            lines.append(f"  L{f.line}: {f.snippet}")
        lines.append(
            "  For each, add `blindfold: <source> — why` on the assertion line or "
            "the comment line above it. Valid sources: spec, rfc, doc, issue, ticket, "
            "math, golden, contract, invariant, manual, standard, example. "
            "Trivial literals (0, 1, -1, \"\", true, false) are exempt."
        )

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
