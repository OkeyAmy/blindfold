---
name: blindfold
description: >
  A discipline for writing test assertions: decide the expected value from intent
  BEFORE looking at what the code returns, and declare where it came from. Use when
  writing or editing tests, assertions, or expected values in any language (Python,
  TypeScript/JavaScript, Go, Rust); when an expected value is a concrete number or
  string; or when the user says "write a test", "blindfold", or asks whether a test's
  expected values are trustworthy. Pairs with smoke-alarm.
---

# blindfold

When you write `assert f(x) == V`, `V` is a claim that the *correct* answer is `V`. If
you got `V` by running `f(x)` and copying the result, you proved nothing — the test now
agrees with the code no matter how wrong the code is.

So: put the blindfold on. Decide what the answer *should* be from the intent, before you
look at output.

## The loop

1. **Before writing the assertion**, answer: *"This should be `V` because <source>."*
   The source must be independent of the implementation — a spec, doc, issue, known
   math, a hand-computed golden value, a contract/invariant. If the only answer is
   "because that's what it returns," stop: go find the intended value first.

2. **Write the assertion with its reason inline:**
   ```
   assert price(100) == 80.0   # blindfold: spec — 20% off $100 is $80
   ```
   The tag goes on the assertion line or the comment line directly above it.
   Valid sources: spec, rfc, doc, issue, ticket, math, golden, contract, invariant,
   manual, standard, example. Trivial literals (0, 1, -1, "", true, false) need none.

3. **Check yourself:**
   ```
   blindfold check <test-file>
   ```
   (After install there is a `blindfold` command on your PATH — run it from inside any
   project. If it is not on PATH, fall back to `python3 <blindfold-dir>/src/blindfold.py
   check <test-file>`.)
   Fix every `UNJUSTIFIED` (you asserted a magic value with no reason) and every
   `CONFESSED` (you admitted it came from output). Re-run until clean.

## Rules

- Never assert a non-trivial literal you cannot justify from intent.
- Never tag a value `spec`/`doc`/… that you actually read off the code — that is lying
  in the diff. If it came from output, the test is asserting current behaviour, not
  correct behaviour; rewrite it against the real intended value.
- The reason is documentation. Write it so a reviewer who never saw the code understands
  why the value is correct.
- blindfold is **strict**: every non-trivial expected literal needs a tag, including
  ones that feel obvious (`status == 200`, `len == 25`). "Obvious" is how wrong values
  slip through — state the claim once. Only `0`, `1`, `-1`, `""`, `true`, `false` are exempt.
- To skip a legacy file you have not migrated, put `blindfold: ignore` in a comment in
  it. Do not use this to dodge writing a reason on new tests.

Pairs with **smoke-alarm** (does the test check anything, and does it die when the code
breaks?). blindfold answers the other half: is what it checks against actually true, and
how do you know?
