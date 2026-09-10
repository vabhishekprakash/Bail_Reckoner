# L-002 — Is a section's prescribed maximum uniform across States?

*(Second entry in the L-series. Kept in its own file only because `LEGAL_DECISIONS.md` is
append-only and this was raised separately; merge on next edit if preferred.)*

**Raised by:** Abhishek, 2026-08-12, from the s.304A state-amendment finding.

## The question

s.479(1) fixes the threshold against "the maximum period of imprisonment specified for that
offence **under that law**". The system treats that maximum as a property of the offence — one
value, valid everywhere in India. India Code's own typesetting suggests otherwise: it prints
**`STATE AMENDMENTS`** blocks inline after a section, and the block following **IPC s.304A**
contains **Himachal Pradesh's s.304-AA**, which carries **imprisonment for life** where s.304A
itself carries **two years**.

*[UNVERIFIED: whether s.304-AA displaces s.304A's maximum for a prosecution in that State, or
creates a distinct offence charged separately, has not been determined by this project. The
observation is that the apparatus exists and is printed as part of the section.]*

If a State amendment can change the maximum for the same charged section, then **the maximum is a
function of jurisdiction as well as of charge variant**, and the engine has **no state
dimension** at all.

## Why it is legal before technical

Same shape as L-001, in a second dimension. L-001 asks whether "that offence" means the section
or the charge as framed; L-002 asks whether it means the section *as in force in the State of
prosecution*. Neither can be answered by choosing a schema, and a schema that omits the dimension
has silently answered "no".

## Why it is dangerous in both directions

Unlike most gaps in this project, the error here is **not one-sided**, which removes the usual
comfort of a conservative default:

* Where the true State maximum is **higher** than the recorded one, the gate-5 threshold is
  understated and the system **over-claims** entitlement. A court catches that.
* Where the true State maximum is **lower**, the threshold is overstated **and gate 0 is
  suppressed** — the absolute-cap detection fails. That is the silent false negative D-010 exists
  to prevent, and nobody appeals it.

There is therefore no single direction to err in, and "pick the higher maximum" is **not** safe
here, unlike D-039's person-level rule.

## Measured scope, 2026-08-12

A mechanical scan for `STATE AMENDMENTS` blocks across all 40 drafted sections found **2**:

| Section | Offence | Regime |
|---|---|---|
| IPC s.379 | Theft | IPC only |
| IPC s.304A | Causing death by negligence | IPC only |

Both are **IPC-side only** — no BNS section in the drafted set carries such a block, consistent
with BNS being recent. **Both sit in the batch-1 priority subset**, so the first twenty rows a
reviewer touches include both known instances.

Two of forty is small, and it is *not* a bound: the scan detects only blocks India Code prints
inline in the stored file, and a different consolidation may print them elsewhere or omit them.

## Interim behaviour coded

Per Abhishek's direction, D-054's refinement applied to a new gap — **name it rather than let
silence imply uniformity**:

* A row whose section carries a `STATE AMENDMENTS` block is **flagged**.
* The report states that a state amendment exists for the section and **has not been evaluated by
  this project**, rather than reporting nothing.
* The flag does not change the verdict and asserts nothing about the amendment's effect.

## What changes on each answer

* *Maximum is uniform* — the blocks are apparatus; drop the flag, record why.
* *Maximum varies by State* — the engine needs a **state input**, penalty rows need a
  jurisdiction key, and every stored report needs the State it was computed for. That is a larger
  change than L-001's per-limb keying and would interact with it multiplicatively.

**Status:** OPEN. **Who can settle it:** a practising advocate. Not this project.


---

## STATUS CHANGE — 2026-08-19 (appended)

**No advocate review is available to this project, permanently** (Abhishek, 2026-08-19).
L-002's "Who can settle it" answer — a practising advocate — names a resource this project
will not have. The question is **open and unresolvable within this project**; the coded
conservative default is the system's permanent behaviour. See
`05_docs/Open_Questions_Register_2026-08-19.md` for the consolidated register and the
safe-default audit.
