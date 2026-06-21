# blindfold

**Assert what should happen — before you look at what does.**

A test's expected value is a claim about *correct behaviour*. The fastest way to get it
wrong is to run the code, see what it returns, and type that in. Now the test agrees
with the code by construction: if the code is buggy, the test enshrines the bug and goes
green forever. This is the single most common way AI-written tests lie.

Every other tool tries to *detect* this after the fact — scanning a finished test and
**guessing** whether `80.0` came from a spec or from output. Guessing is the wrong move.

blindfold doesn't guess. It makes you **declare** where each expected value comes from,
right next to it, and it refuses the one source that poisons a test: the code's own
output.

```python
assert price(100) == 80.0    # blindfold: spec — 20% off $100 is $80      ✓ justified
assert price(50)  == 40.0                                                  ✗ unjustified
assert price(20)  == 16.0    # blindfold: output — what it returned        ✗ confessed
```

If you can't name an a-priori reason for a value, you didn't write a test. You took a
photograph of the implementation.

## Design stance

I built this because the honest fix for fake tests isn't a smarter detector — it's a
discipline that makes the failure mode *impossible to express silently*. You either
state why the answer is right, or the check fails. The reason becomes a durable,
auditable record of intent: anyone reading the suite later can see *why* `80.0` is
correct, not just that the code currently produces it.

It pairs with [smoke-alarm](https://github.com/OkeyAmy/smoke-alarm): smoke-alarm asks
*"does this test check anything, and does it die when the code breaks?"*; blindfold asks
*"is the thing it checks against actually true, and how do you know?"* Different
questions, same goal — tests that can fail for the right reason.

## Install

```bash
git clone https://github.com/OkeyAmy/blindfold
cd blindfold
./install.sh          # copies skill to all present tool dirs, registers PostToolUse hook
./install.sh doctor   # verify install + Python version + self-tests
./install.sh uninstall
```

**What install does:**
- Copies the skill to `~/.claude/skills/blindfold/`, `~/.codex/skills/blindfold/`, and
  any other AI tool directories it finds.
- Registers a `PostToolUse` hook in your agent's config so blindfold fires automatically
  on every `Write`/`Edit` to a test file — no human trigger needed.

Requires Python ≥ 3.8. No dependencies beyond the standard library.

## Use

After `./install.sh` there is a `blindfold` command on your PATH — any agent, in any
project, runs:

```bash
blindfold check path/to/tests          # human report, exit 1 if any unjustified/confessed
blindfold check path/to/tests --json   # machine-readable
```

Without installing (from a clone), the equivalent is `python3 src/blindfold.py check …`.

Languages: Python, TypeScript/JavaScript, Go, Rust.

## The grammar

A reason is a comment tag on the assertion line, or the comment line directly above it:

```
<comment> blindfold: <source> — <free text why>
```

**Valid sources** (independent of the implementation): `spec`, `rfc`, `doc`, `issue`,
`ticket`, `math`, `golden`, `contract`, `invariant`, `manual`, `standard`, `example`.

**Confessed sources** (rejected — they admit the value came from the code): `output`,
`actual`, `current`, `returned`, `observed`, `snapshot`, `repl`, `result`.

Trivial literals (`0`, `1`, `-1`, `""`, `true`, `false`) need no reason.

## Strict by design

blindfold flags **every** non-trivial expected literal, not just ones that "look magic."
`assert status == 200`, `assert len(items) == 25`, `assert role == "admin"` all need a
tag. This is deliberate: *every* expected value is a claim about correct behaviour, and
"it's obvious" is how a wrong value sneaks through. If `200` is the documented success
code, say so once — `# blindfold: standard — HTTP 200 OK` — and the claim is now on the
record for the next reader. A discipline that exempts "obvious" values stops being a
discipline.

The cost is real: on a fresh suite, expect to tag a lot. Two escape hatches keep that
survivable:

- **Per file:** put `blindfold: ignore` in a comment anywhere in a file and blindfold
  skips it entirely. Use this on legacy tests you have not migrated yet.
- **Per value:** trivial literals are always exempt.

**Adopting on an existing codebase:** drop `# blindfold: ignore` at the top of every
current test file, then remove the marker file-by-file as you migrate. New test files get
the discipline from day one; old ones are opt-in. No flood, no big-bang rewrite.

## As an agent skill

After `./install.sh`, the `SKILL.md` is in your tool's skills directory and a
`PostToolUse` hook runs blindfold on every test file the agent writes. The agent
sees the verdict immediately and must justify or remove the flagged value before
continuing. No script to remember to run — the discipline is internal.

Tool compatibility: Claude Code, Codex, Cursor, any tool that loads skills from
`~/.claude/skills/`, `~/.codex/skills/`, `~/.agents/skills/`, or `~/.cursor/skills/`.

## Self-test

```bash
python3 tests/test_blindfold.py   # 8/8 — python + ts/go/rust + file-level ignore
python3 tests/test_ast_scan.py    # 10/10 — Python AST: ignores non-assertions, catches real ones
```

## How detection works

- **Python: AST-based.** blindfold parses the file and inspects only real assertions
  (`assert a == b`, the `assertEqual` family). It does **not** flag `==` in an `if`, the
  `if __name__ == "__main__"` guard, or `==` that appears inside a string literal — those
  are not assertions. It reads the expected literal's exact line, so a tag works even in a
  multi-line assertion.
- **TypeScript / Go / Rust: line-regex** (a tag may need to sit on the literal's line).
  These get the AST treatment as it lands per language.

## Honest limits

- It checks expected-value **literals**. Assertions whose expected value is a computed
  expression aren't pinned to a literal, so blindfold doesn't demand a reason for them —
  those are smoke-alarm's and provenance's territory.
- It trusts your tag. `blindfold: spec` on a value you actually copied from output will
  pass — but you had to lie in writing to do it, and that lie is now in the diff for a
  reviewer to catch. Making dishonesty explicit is the point.

## License

MIT.
