# LEGAL_DECISIONS.md — legal-characterisation questions (L-series)

Questions that must be answered **as law** before they can be answered as schema, data or code.
Distinct from `01_law\OPEN_LEGAL_QUESTIONS.md` (OLQ-series), which asks what a provision *means*;
this file asks what a statutory concept *attaches to*, where the answer determines how the system
is built rather than what it outputs on a given case.

Append-only. Each entry: the question, why it is legal before it is technical, what is currently
built, what changes on each answer, and who can settle it.

Created 2026-08-12 (session 12) on Abhishek's instruction.

---

## L-001 — What does the "maximum period of imprisonment specified for that offence" in s.479(1) attach to: the section, or the charge as framed?

**Raised by:** the First Principles advisor in the (incomplete) council of 2026-08-12 —
`05_docs\council-transcript-2026-08-12-INCOMPLETE.md`. Logged here because the finding is a
**legal-characterisation question before it is a schema one**, and this project cannot settle it.

**The question.** s.479(1) fixes the threshold as one-half (or one-third) of "the maximum period
of imprisonment specified for that offence under that law". The system currently models that
maximum as a property of an **offence section** — one row, one maximum. Indian criminal law does
not appear to work that way. A single section routinely carries several punishment limbs with
different maxima, selected by facts about the *case*:

* **Quantity.** NDPS penalties differ by small / intermediate / commercial quantity.
* **Capacity of the accused.** Criminal breach of trust is graded across IPC ss.406–409 —
  plain entrustment, carrier, clerk or servant, public servant or banker — with sharply different
  maxima; BNS s.316's sub-sections mirror it. *[UNVERIFIED — flagged by Abhishek from
  recollection as where to look, not as what will be found.]*
* **Victim age or aggravating circumstance.** The sexual-offence sections carry age-graded limbs.
* **Repeat conviction.** BNS s.303(2) carries a repeat-conviction proviso.
* **Degree of harm.** Hurt / grievous hurt / hurt by dangerous weapons.

So "the offence" in s.479(1) may mean the section, or it may mean the offence **as charged** —
the specific limb the charge-sheet invokes. The two give different thresholds for the same person.

**Why this is legal before technical.** Choosing a data model here is choosing a reading of the
statute. If "that offence" means the section, a single maximum per section is right and the
highest limb governs. If it means the charge as framed, then a row per limb is right and the
system must be told which limb is charged — a new required input, and a new abstention when it is
unknown. **No schema can be neutral between those readings**, which is why this is not a
refactoring decision.

**Why it is urgent.** It is load-bearing in the dangerous direction. A maximum that is **too
high** inflates the gate-5 threshold *and* suppresses gate 0 — the absolute-cap detection. That
is a **false negative**: the person stays in custody and, per D-010's whole rationale, nobody
appeals a machine's silence. A too-low maximum produces an over-claim a court catches.

**What is currently built.** One row per section; the *highest* maximum among charged offences
governs the person-level threshold (D-039, already marked `[UNVERIFIED]`). Where a maximum cannot
be resolved, the engine returns `OFFENCE_NOT_IN_DATABASE` and never guesses.

**What changes on each answer.**
* *"The section"* — current model stands; D-039 is confirmed; row count stays ~40.
* *"The charge as framed"* — re-key on `(regime, section, sub-section, variant)`, one row per
  punishment limb with its own quoted text, page citation, maximum **and minimum**; the charged
  limb becomes a required input; unknown limb → `OFFENCE_NOT_IN_DATABASE` (D-061, proposed).
  Estimated row count **~81** on the current 20-offence seed set.

**Who can settle it.** A practising advocate or law-faculty reviewer. **Not this project, and not
the team** — CLAUDE.md §7 is explicit that an agent or team member labelling and then being
scored against those labels measures agreement with the labeller, not legal correctness.

**Status:** OPEN. Conservative default coded: one row per section, highest maximum governs,
`[UNVERIFIED]`. Related: OLQ-2 (which offence's maximum governs when several are charged) asks a
narrower version of the same question at the *person* level; L-001 asks it at the *section* level.


---

## STATUS CHANGE — 2026-08-19 (appended)

**No advocate review is available to this project, permanently** (Abhishek, 2026-08-19).
L-001's "Who can settle it" answer — a practising advocate — names a resource this project
will not have. The question is **open and unresolvable within this project**; the coded
conservative default is the system's permanent behaviour. See
`05_docs/Open_Questions_Register_2026-08-19.md` for the consolidated register and the
safe-default audit.
