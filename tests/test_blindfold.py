#!/usr/bin/env python3
"""Self-test for blindfold. The fixture encodes each expected status in the test name;
blindfold must classify each assertion's expected value the same way.

Run:  python3 tests/test_blindfold.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))
import blindfold  # noqa: E402

# function-name fragment -> expected blindfold status (None = should be exempt/no finding)
EXPECTED = {
    "test_justified_inline": "justified",
    "test_justified_above": "justified",
    "test_unjustified": "unjustified",
    "test_confessed": "confessed",
    "test_trivial_exempt": None,
}


def main() -> int:
    fx = ROOT / "fixtures" / "test_pricing.py"
    result = blindfold.scan_file(fx)
    lines = fx.read_text().splitlines()

    # map each finding to the test function it sits in
    def enclosing(line_no: int) -> str:
        name = ""
        for i in range(line_no - 1, -1, -1):
            s = lines[i].strip()
            if s.startswith("def "):
                return s[4:].split("(")[0]
        return name

    got: dict[str, str] = {}
    for f in result.findings:
        got[enclosing(f.line)] = f.status

    total = passed = 0
    failures = []
    for fn, want in EXPECTED.items():
        total += 1
        actual = got.get(fn)
        if want is None:
            ok = fn not in got  # trivial line must produce no finding
        else:
            ok = actual == want
        if ok:
            passed += 1
        else:
            failures.append(f"{fn}: want {want}, got {actual}")

    # multi-language coverage: aggregate status counts across ts/go/rust fixtures
    multi = ROOT / "fixtures" / "multi"
    counts = {"justified": 0, "unjustified": 0, "confessed": 0}
    langs = set()
    for p in sorted(multi.iterdir()):
        r = blindfold.scan_file(p)
        if r is None:
            continue
        langs.add(r.lang)
        for f in r.findings:
            counts[f.status] += 1
    want_counts = {"justified": 3, "unjustified": 3, "confessed": 1}
    want_langs = {"ts", "go", "rust"}
    total += 2
    if counts == want_counts:
        passed += 1
    else:
        failures.append(f"multi-lang counts: want {want_counts}, got {counts}")
    if langs == want_langs:
        passed += 1
    else:
        failures.append(f"multi-lang coverage: want {want_langs}, got {langs}")

    # file-level opt-out: a file declaring `blindfold: ignore` is skipped entirely,
    # even though it contains an otherwise-unjustified literal.
    import tempfile
    total += 1
    with tempfile.NamedTemporaryFile("w", suffix="_test.py", delete=False) as tf:
        tf.write("# blindfold: ignore\ndef test_x():\n    assert tax(1000) == 230.0\n")
        ignored_path = Path(tf.name)
    try:
        r = blindfold.scan_file(ignored_path)
        if r is not None and r.findings == []:
            passed += 1
        else:
            findings = None if r is None else r.findings
            failures.append(f"ignore marker: want no findings, got {findings}")
    finally:
        ignored_path.unlink(missing_ok=True)

    print(f"{passed}/{total} checks passed")
    for f in failures:
        print(f"  - {f}")
    if not failures:
        print("OK — blindfold classifies correctly across python/ts/go/rust")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
