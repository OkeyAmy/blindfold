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

## Use

```bash
python3 src/blindfold.py check path/to/tests        # human report, exit 1 if any unjustified
python3 src/blindfold.py check path/to/tests --json  # machine-readable
```

Languages: Python, TypeScript/JavaScript, Go, Rust. Requires Python ≥ 3.9.

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

## As an agent skill

Install `SKILL.md` into your AI tool's skills directory so the agent adopts the
discipline while writing tests: decide the expected value from intent first, annotate
it, run `blindfold check`, fix anything unjustified or confessed.

## Self-test

```bash
python3 tests/test_blindfold.py   # 5/5 — justified / unjustified / confessed / trivial
```

## Honest limits

- It checks expected-value **literals**. Assertions whose expected value is a computed
  expression aren't pinned to a literal, so blindfold doesn't demand a reason for them —
  those are smoke-alarm's and provenance's territory.
- It trusts your tag. `blindfold: spec` on a value you actually copied from output will
  pass — but you had to lie in writing to do it, and that lie is now in the diff for a
  reviewer to catch. Making dishonesty explicit is the point.
- Detection is line-based, not AST. Multi-line assertions may need the tag on the line
  with the literal.

## License

MIT.
