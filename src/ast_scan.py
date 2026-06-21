#!/usr/bin/env python3
"""blindfold Python AST scanner.

Line-regex cannot tell an assertion from an ``if``, or code from a string. It flags
``if __name__ == "__main__"``, control-flow comparisons, and ``==`` that appears inside
a string literal (test fixtures that embed code as data). Those are all false positives.

For Python we parse the AST and inspect only real assertions — ``assert a == b`` and the
unittest ``assertEqual`` family — reading the expected literal's exact line so a
``blindfold:`` tag on that line, or the line above, is found even in a multi-line
assertion. Other languages keep the regex scanner until they get the same treatment.
"""

from __future__ import annotations

import ast
from pathlib import Path

from blindfold import Finding, FileResult, classify, find_tag

# unittest equality assertions whose literal arguments are expected values.
EQUALITY_CALLS = {
    "assertEqual", "assertNotEqual", "assertAlmostEqual", "assertNotAlmostEqual",
}


def _literal(node: ast.AST) -> tuple[bool, bool, str]:
    """Return (is_literal, is_trivial, text) for a constant or signed-constant node.

    Trivial literals (0, 1, -1, "", True, False) need no justification, matching the
    regex scanner's TRIVIAL set."""
    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, bool):
            return True, True, repr(v)
        if isinstance(v, (int, float)):
            return True, v in (0, 1, -1), repr(v)
        if isinstance(v, str):
            return True, v == "", repr(v)
        return False, True, ""  # None, bytes, … are not policed expected values
    if (isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd))
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (int, float))
            and not isinstance(node.operand.value, bool)):
        v = -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
        return True, v in (0, 1, -1), repr(v)
    return False, True, ""


def _expected_literals(tree: ast.AST) -> list[ast.AST]:
    """Every non-trivial expected-value literal that sits in a real assertion."""
    found: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare):
            cmp = node.test
            if not any(isinstance(op, (ast.Eq, ast.NotEq)) for op in cmp.ops):
                continue  # only equality asserts a value; thresholds are out of scope
            for operand in (cmp.left, *cmp.comparators):
                is_lit, triv, _ = _literal(operand)
                if is_lit and not triv:
                    found.append(operand)
        elif isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) \
                else getattr(node.func, "id", "")
            if name in EQUALITY_CALLS:
                for arg in node.args:
                    is_lit, triv, _ = _literal(arg)
                    if is_lit and not triv:
                        found.append(arg)
    return found


def scan_python(path: Path, text: str) -> FileResult:
    """Scan Python source for assertion expected values lacking an a-priori source.

    Raises SyntaxError if the file does not parse; the caller decides whether to fall
    back to the regex scanner (CLI) or treat it as unverified (hook)."""
    tree = ast.parse(text)
    lines = text.splitlines()
    result = FileResult(path=str(path), lang="python")
    seen: set[tuple[int, int]] = set()
    for node in sorted(_expected_literals(tree), key=lambda n: (n.lineno, n.col_offset)):
        key = (node.lineno, node.col_offset)
        if key in seen:
            continue
        seen.add(key)
        idx = node.lineno - 1
        snippet = lines[idx].strip() if 0 <= idx < len(lines) else ""
        tag = find_tag(lines, idx)
        if tag is None:
            result.findings.append(Finding(node.lineno, "unjustified", "", snippet))
        else:
            status = classify(tag.group(1))
            result.findings.append(Finding(node.lineno, status, tag.group(1).lower(), snippet))
    return result
