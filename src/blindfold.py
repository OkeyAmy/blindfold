#!/usr/bin/env python3
"""blindfold — assert what SHOULD happen before you look at what does.

The deepest test-quality bug is using what the code *did* (a posteriori) as the
definition of what it *should do* (a priori). A test then locks in the bug and passes
forever. Tools that scan finished tests can only *guess* whether an expected value came
from intent or from output.

blindfold removes the guessing: every expected value in a test must declare its reason
inline, and the reason may not be "that's what it returned." If you can't articulate
why a value is correct, blindfold fails — you wrote a photograph of the code, not a test.

Declare a reason with a comment tag on the assertion line or the line above it:

    assert price(100) == 80.0      # blindfold: spec — 20% off $100 is $80
    expect(slug("A B")).toBe("a-b")  // blindfold: doc — slug lowercases, spaces->dash

Allowed sources are grounds independent of the implementation (spec, rfc, doc, issue,
math, golden, contract, invariant, manual). Sources that confess the value came from the
code (output, actual, current, returned, observed, snapshot, repl) are rejected.

Usage:
  blindfold check <file-or-dir> [--json] [--strict]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

EXT_TO_LANG = {
    ".py": "python", ".ts": "ts", ".tsx": "ts", ".js": "ts", ".jsx": "ts",
    ".go": "go", ".rs": "rust",
}
TEST_HINTS = ("test", "spec", "__tests__")

# Grounds independent of the implementation — a real a-priori source.
VALID_SOURCES = {
    "spec", "rfc", "doc", "docstring", "issue", "ticket", "math",
    "golden", "contract", "invariant", "manual", "standard", "example",
}
# Sources that admit the value was taken from the code's own behaviour.
CONFESSED_SOURCES = {
    "output", "actual", "current", "returned", "observed", "snapshot",
    "repl", "ran", "result", "behaviour", "behavior",
}

# An assertion that pins a concrete expected literal (number or quoted string).
_NUM = r"-?\d+(?:\.\d+)?"
_STR = r'"[^"\n]*"|\'[^\'\n]*\'|`[^`\n]*`'
_LIT = rf"(?:{_NUM}|{_STR})"
EXPECTED_LITERAL = {
    "python": [re.compile(rf"==\s*{_LIT}"), re.compile(rf"assertEqual\([^,]+,\s*{_LIT}")],
    "ts": [re.compile(rf"\.(?:toBe|toEqual|toStrictEqual)\(\s*{_LIT}\s*\)")],
    "go": [re.compile(rf"assert\.Equal\(\s*t,\s*{_LIT}"), re.compile(rf"!=\s*{_LIT}\s*\{{")],
    "rust": [re.compile(rf"assert_eq!\([^,]+,\s*{_LIT}")],
}
# Trivial literals are exempt — nobody needs to justify 0/1/-1/""/true/false.
TRIVIAL = {"0", "1", "-1", '""', "''", "``", "true", "false"}

TAG = re.compile(r"blindfold:\s*([A-Za-z]+)\b\s*[-:—]?\s*(.*)$")


@dataclass
class Finding:
    line: int
    status: str   # justified | unjustified | confessed
    source: str
    snippet: str


@dataclass
class FileResult:
    path: str
    lang: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def unjustified(self) -> int:
        return sum(1 for f in self.findings if f.status != "justified")


def is_trivial(line: str, lang: str) -> bool:
    # If every expected literal on the line is trivial, skip it.
    lits = re.findall(_LIT, line)
    return all(l in TRIVIAL for l in lits) if lits else True


def has_expected_literal(line: str, lang: str) -> bool:
    return any(p.search(line) for p in EXPECTED_LITERAL.get(lang, []))


def find_tag(lines: list[str], idx: int) -> re.Match | None:
    """A reason on this line, or on the comment line directly above it."""
    m = TAG.search(lines[idx])
    if m:
        return m
    if idx > 0:
        prev = lines[idx - 1].strip()
        if prev.startswith(("#", "//", "*")) or "blindfold:" in prev:
            return TAG.search(lines[idx - 1])
    return None


def classify(source: str) -> str:
    s = source.lower()
    if s in CONFESSED_SOURCES:
        return "confessed"
    if s in VALID_SOURCES:
        return "justified"
    return "unjustified"  # unknown tag word — not a recognised ground


def scan_file(path: Path) -> FileResult | None:
    lang = EXT_TO_LANG.get(path.suffix.lower())
    if lang is None:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    result = FileResult(path=str(path), lang=lang)
    # File-level opt-out: a legacy file you have not migrated yet declares it once and
    # is skipped entirely. Checked before per-line scanning so the marker line itself is
    # never mistaken for an unjustified tag.
    if "blindfold: ignore" in text:
        return result
    if lang == "python":
        # Python gets a real AST scanner: it flags expected literals only in actual
        # assertions, never in `if`/`__main__`/string-literal false positives. On a
        # syntax error we fall back to the regex scan rather than crash.
        try:
            from ast_scan import scan_python
            return scan_python(path, text)
        except SyntaxError:
            pass
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not has_expected_literal(line, lang) or is_trivial(line, lang):
            continue
        tag = find_tag(lines, i)
        if tag is None:
            result.findings.append(Finding(i + 1, "unjustified", "", line.strip()))
        else:
            status = classify(tag.group(1))
            result.findings.append(Finding(i + 1, status, tag.group(1).lower(), line.strip()))
    return result


def iter_targets(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return [p for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix.lower() in EXT_TO_LANG
            and any(h in p.as_posix().lower() for h in TEST_HINTS)]


def render(results: list[FileResult]) -> str:
    out: list[str] = []
    total = clean = 0
    for r in results:
        if not r.findings:
            continue
        out.append(f"\n{r.path}  [{r.lang}]")
        for f in r.findings:
            total += 1
            if f.status == "justified":
                clean += 1
                mark = f"justified ({f.source})"
            elif f.status == "confessed":
                mark = f"CONFESSED ({f.source}: value taken from the code)"
            else:
                mark = "UNJUSTIFIED (no a-priori reason given)"
            out.append(f"  L{f.line}: {mark}")
            out.append(f"        {f.snippet}")
    bad = total - clean
    out.append(f"\n== {clean}/{total} expected values are justified; {bad} need a reason ==")
    if bad:
        out.append("Add `blindfold: <source> — why` (source: spec/doc/issue/math/golden/…). "
                    "If the only honest reason is 'that's what it returned', the test is "
                    "asserting a bug — find the intended value first.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="blindfold")
    sub = ap.add_subparsers(dest="cmd")
    chk = sub.add_parser("check", help="check expected values are justified")
    chk.add_argument("target")
    chk.add_argument("--json", action="store_true")
    chk.add_argument("--strict", action="store_true",
                     help="exit non-zero on confessed/unjustified (default: only on these too)")
    args = ap.parse_args(argv)

    if args.cmd != "check":
        ap.print_help()
        return 2

    root = Path(args.target)
    if not root.exists():
        print(f"error: path not found: {root}", file=sys.stderr)
        return 2

    results = [r for r in (scan_file(p) for p in iter_targets(root)) if r]
    bad = sum(r.unjustified for r in results)

    if args.json:
        print(json.dumps([
            {"path": r.path, "lang": r.lang,
             "findings": [{"line": f.line, "status": f.status, "source": f.source}
                          for f in r.findings]}
            for r in results], indent=2))
    else:
        print(render(results))

    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
