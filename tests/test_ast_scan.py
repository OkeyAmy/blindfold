#!/usr/bin/env python3
"""Real-input tests for the Python AST scanner.

Each case is genuine Python source parsed by the actual scan path (scan_python ->
ast.parse). The "no finding" cases are the false positives the line-regex produced and
the AST scanner must not; the status cases are true positives it must still catch.

Run:  python3 tests/test_ast_scan.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))
from ast_scan import scan_python  # noqa: E402


def statuses(src: str) -> list[str]:
    return [f.status for f in scan_python(Path("<t>"), src).findings]


# Things the regex scanner wrongly flagged — the AST scanner must produce NO finding.
NO_FINDING = {
    "module_main_guard": "if __name__ == \"__main__\":\n    run()\n",
    "control_flow_if": "def test_x():\n    if status() == \"ok\":\n        pass\n",
    "equality_inside_string": "def test_x():\n    msg = \"assert add(2, 3) == 5\"\n    use(msg)\n",
    "trivial_literal": "def test_x():\n    assert price(0) == 0\n",
    "threshold_not_equality": "def test_x():\n    assert score() < 100\n",
}

# True positives — the scanner must still flag and classify these.
STATUS = {
    "unjustified_assert": ("def test_x():\n    assert add(2, 3) == 5\n", "unjustified"),
    "justified_inline": (
        "def test_x():\n    assert add(2, 3) == 5  # blindfold: math — 2+3 is 5\n",
        "justified",
    ),
    "confessed_inline": (
        "def test_x():\n    assert tax(100) == 23.0  # blindfold: output — what it returned\n",
        "confessed",
    ),
    "assertEqual_call": (
        "import unittest\n"
        "class TestX(unittest.TestCase):\n"
        "    def test_x(self):\n"
        "        self.assertEqual(compute(), 42)\n",
        "unjustified",
    ),
    # multi-line assertion: tag sits on the literal's line, which line-regex could miss.
    "multiline_justified": (
        "def test_x():\n"
        "    assert (\n"
        "        compute()\n"
        "        == 42  # blindfold: spec — defined as 42\n"
        "    )\n",
        "justified",
    ),
}


def main() -> int:
    passed = total = 0
    failures: list[str] = []

    for name, src in NO_FINDING.items():
        total += 1
        st = statuses(src)
        if st == []:
            passed += 1
        else:
            failures.append(f"{name}: expected NO finding, got {st}")

    for name, (src, want) in STATUS.items():
        total += 1
        st = statuses(src)
        if st == [want]:
            passed += 1
        else:
            failures.append(f"{name}: want [{want}], got {st}")

    print(f"{passed}/{total} checks passed")
    for f in failures:
        print(f"  - {f}")
    if not failures:
        print("OK — AST scanner ignores non-assertions and catches real expected values")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
