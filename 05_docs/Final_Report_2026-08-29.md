# Bail Reckoner: Final Comprehensive Report

**Date:** 2026-08-29 · **Prepared for:** Vallamalla Abhishek Prakash (team lead)
**Supersedes** `Final_Report_2026-08-26.md` (kept for the record; this file governs).
Ordered by Abhishek's directive of 2026-08-29, items 9 and 10: open with the governing
fact, cover everything, generate "what remains" from the register, and state plainly
what the project is not. *(Prose restyled 2026-09-10 for the public release; every
fact, figure and date is unchanged from the 2026-08-29 original.)*

---

## 1. The governing fact

**Zero verified penalty rows exist, so the system computes nothing about any real
offence.** Every gate, report, filing, endpoint, evaluation and test operates over
synthetic fixtures labelled as such, or over statutory text whose derived values await
human verification. The engine's correctness is proved; its first real computation
happens when a human signs the first row of the review queue. No machine channel,
including the new cross-channel reconciliation, verifies or promotes a row. The
reconciliation reduces the owner's reading; it does not replace his signature.

## 2. What this project is NOT

Stated without softening:

* **Not operational.** No verified rows, no deployment, and no real case has ever been
  computed.
* **Not advocate-reviewed**, and permanently so. No advocate or law-faculty reviewer is
  available to this project, every Tier 2 label measures agreement with a non-advocate
  labeller, and every open legal question stays open forever with a conservative coded
  default.
* **Not tested on real charge sheets.** Data-protection discipline: no real accused
  person's data exists anywhere in the project. Extraction is measured on synthetic
  text only, and its perfect recall there is explicitly optimistic.
* **Carrying no model in Layer B.** The extraction layer is a seam: a deterministic
  baseline and a human confirmation gate. Fine-tuning is not feasible in this
  environment and no trained extractor exists. The Extended Abstract's promised
  capability is not present, and the record says so wherever the layer is described.

## 3. The four states of "built"

| Layer | State | What backs the claim |
|---|---|---|
| **C, engine** | **Built and proved** | Six gates; a test per gate and proviso; adversarial gate-2 tests; byte-comparable goldens for every report and filing shape; Tier 1 arithmetic independently recomputed |
| **A, retrieval** | **Built and measured** | 2,245 sections, 8 acts, SHA and as-on date on every chunk; Recall@k and MRR by query class; three findings (section 6) |
| **D, precedent** | **Built and unscored, over a corpus permanently labelled INCOMPLETE** | 3 of 4 judgments (Ramakrishna permanently unacquired); verbatim-extract-only by construction; scoring optional, and the self-scored pass is never an evaluation figure |
| **B, extraction** | **Seam built, no model, none possible here** | Deterministic baseline plus named-human confirmation; P/R/F1 of 1.000/1.000/1.000 *measuring a deterministic gazetteer over 38 known sections in synthetic text, a floor rather than charge-sheet extraction*; recall optimistic even as a floor |

Also built: the REST API (honesty envelope; hash-chained append-only audit log with
out-of-log head state); the server-rendered interface under the nine D-077 constraints
(stack ruled server-first, D-084); the deterministic stdlib PDF renderer (D-073, with
the PDFium leg verified and Acrobat plus one physical print remaining at this date);
the D-088 open-items register with its generated awaiting list; and the D-089 OCR
channel powering the queue reconciliation.

## 4. Every open legal question, and its permanent conservative default

No advocate will ever close these; each is coded to a default that surfaces the
uncertainty. Register: `05_docs/Open_Questions_Register_2026-08-19.md`.

* **OLQ-1** Category C bar: gate 3 is a FLAG, never terminal; arithmetic shown;
  provision quoted; human review. Whether NDPS follows *Badshah* is expressly
  unsettled.
* **OLQ-2** Several offences: the highest maximum governs; the D-075 band shows both
  qualifying dates with `CONTESTED_THRESHOLD_BASIS`.
* **OLQ-3** s.479(2) against the bond route: the bar reaches both; `CONTESTED`.
* **OLQ-4** POCSO: factual limb closed (`VERIFIED_ABSENT`; *Antil* itself names no
  POCSO). The (c)/(d) choice was ruled on 2026-08-26: the flag stays on D-054's
  restated four-part basis, and the remaining limb stays open like every OLQ but
  awaits no ruling.
* **OLQ-5** Single FIR, multiple sections: NARROW default; `CONTESTED_479_2_SCOPE`.
* **OLQ-6** Arrest against first remand: arrest is the clock; both captured; any
  divergence flagged.
* **OLQ-7** The Explanation's excluded days: an input, default zero, never computed by
  the engine. Since 2026-08-29 a self-contradictory exclusion (more excluded or break
  days than days detained) is refused, never floored (section 7, instance 6).
* **OLQ-8** The gate-3 set: *Antil*'s named list only, with the permanent
  non-exhaustive standing line on every report and filing.
* **OLQ-9, 9a, 10** Counting conventions: conservative defaults per D-047, each tested.
* **OLQ-11** Cap basis: the D-066 band with `CONTESTED_CAP_BASIS`; gate 0 is never
  masked.
* **L-001** Per-limb keying: an unnamed limb on a multi-limb section abstains.
* **L-002** State amendments: uniformity is unprovable from stored consolidations, so
  the uniformity note stands unconditionally on every report and inside every filing.

Any `CONTESTED_*` flag hard-blocks the s.479(3) filing. There is no "ineligible"
verdict (D-010); refusals are outputs, not absences.

## 5. Every recorded divergence from the Extended Abstract

1. SQLite, not PostgreSQL plus MongoDB (D-027).
2. Structured-form input at MVP; OCR of charge sheets out of scope (D-026). The D-089
   OCR channel reads statute pages for reconciliation, not charge sheets, and changes
   nothing here.
3. Multilingual is a recorded scope limit (D-087, ruled): English-only documents,
   localisable interface chrome.
4. FAISS declined; exact numpy search instead (D-082).
5. The cross-encoder is excluded from the shipped retrieval configuration. It was the
   abstract's named final stage, and it was excluded on measurement (section 6), not
   preference.
6. RAGAs dropped as a reasoned divergence (D-083).
7. Server-rendered UI first, not React (D-084, ruled); a React client remains addable
   over the unchanged API.
8. No fine-tuned extraction model, which is infeasible here; the seam ships instead,
   with its qualification attached.

## 6. The retrieval findings (claim class: retrieval measurement)

* **Cross-encoder degradation.** Natural-language R@10 fell 0.921 → 0.684 (−25.7%);
  the reranker demotes punishment sections below their definitional cousins. This
  independently reproduces IBPS's degradation finding, against the abstract's own
  named component.
* **Citation-query poisoning.** Dense retrieval scores 0.000 on citation queries, and
  through rank fusion the zero poisons the hybrid (citation R@10 of 0.842 for BM25
  alone against 0.158 for the hybrid). A deterministic regex router restores the best
  of both.
* **Cross-act collision is the majority case.** 510 of 723 distinct section numbers
  (about 70%) exist in more than one act; unmitigated, an act-less citation query was
  silently wrong in the majority case. Mitigated (D-086): one labelled chunk per
  colliding act plus an ambiguity note, choosing none.

## 7. The failure shape: six instances

A plausible answer where a refusal belongs:

1. The `max(1, ...)` limb floor: a failed detection became "one limb".
2. The counterpart ternary: a fabricated cross-code mapping.
3. The TOC discard: genuine sections silently dropped (and the em-dash proxy invariant
   it exposed).
4. The omitted unresolved extraction candidate, indistinguishable from no candidate.
5. Cross-act collision in retrieval, mitigated by D-086 after the census showed the
   ambiguity is the majority case.
6. **The custody contradiction floor**, found 2026-08-29 by a directed adversarial
   audit hunting precisely this shape: `max(0, elapsed − breaks − excluded)` turned
   self-contradictory inputs into a plausible zero effective custody, which
   *under*-claims, the dangerous direction under D-010. Now refused with the
   contradiction named; the test that had pinned the floor as correct was rewritten to
   pin the refusal. The same audit hardened three silent paths in the precedent-corpus
   builder (a missing judgment, a missing provenance hash, and an empty page
   extraction were all absorbed while `CORPUS_STATUS` kept asserting "3 of 4 on
   disk"; all three now refuse) and corrected the review-queue header's page-index
   convention, which was off by one page (the stored index is 0-based; a 1-based
   viewer needs N+1).

The audit's negative results are also on record (PROGRESS, round 21): the remaining
clamps, `or`-defaults and `except` clauses in production code were each inspected and
cleared, with reasons. One observation was reported rather than built: engine refusals
surfaced as HTTP 500s through the API, loud but reason-less for the caller, and the
translation layer was the owner's call. *(It was built three days later, D-092.)*

## 8. The cross-channel reconciliation (claim class: cross-channel agreement measurement)

Every cited queue page was re-read by a second, independent channel: rasterised
(pypdfium2) and read by OCR (RapidOCR, D-089), never touching the PDF text layer. The
result was compared with the stored text-layer extraction on mechanically parsed facts
(term maxima, mandatory minima, life and death mentions, limb count), through one
shared parser so parser quirks cancel out.

**41 sections (86 rows): 26 agree · 13 disagree · 2 the OCR could not read. Agreement
rate over readable sections: 26/39 = 0.667.** This is not a verification and not an
accuracy figure, because two machines can be wrong together, and it blends with
nothing. Document: `04_eval/cross_channel_reconciliation_2026-08-29.md`, disagreements
first, each with both readings side by side and the page image cropped to the section;
unreadable sections listed with reasons. The sanity-pass row IPC s.304A is itself a
disagreement (the OCR channel read a mandatory minimum out of the state-amendment
apparatus), which is exactly the hazard that row leads the queue to demonstrate.

## 9. The claim-class table, with no blended figures

| Claim | Class |
|---|---|
| Gate arithmetic, thresholds, qualifying dates | **Tier 1**: independently recomputed; the only claimable accuracy |
| Golden-set legal-judgement labels | **Tier 2**: labels not advocate-verified, indicative only |
| Layer A Recall@k and MRR | **Retrieval measurement**: no legal judgement involved |
| Layer B P/R/F1 of 1.000/1.000/1.000 | **Qualified floor**: caption mandatory; recall optimistic |
| Layer D self-scores (15 R, 16 P, 5 I of 36) | **Self-scored**: never an evaluation figure |
| Queue reconciliation 26/39 = 0.667 | **Cross-channel agreement**: not verification, not accuracy |
| "Verified against the gazette" (the s.479 text) | Document verification, character-level, provenance recorded |
| Anything about real offences | **No claim possible: zero verified rows** |

## 10. Verification of this state

* **Working checkout:** full suite of **439 passed plus 1 visible skip** at commit
  `a1d36e6` (reconciled: 427 prior, plus 9 OCR-channel, 2 custody and 1 precedent);
  `ruff` and `mypy` clean.
* **Cold clone:** a fresh `git clone` into an isolated gitignored directory, a fresh
  venv installed from `requirements.lock` (75 pins), and the corpus rebuilt from the
  committed PDFs (2,245 chunks, identical to the working checkout). **The first clone
  failed, and the failure is the finding:** 7 golden tests failed at `a1d36e6` because
  the decision-table YAML was absent from `.gitattributes`, checked out with Windows
  line endings, and so changed the content hash that stamps every output's statute
  version. The working checkout could never see this; only a cold clone could. (The
  same lesson as the em-dash proxy: an invariant fixed for the language YAMLs was
  never checked across every hashed source.) Fixed at `4df1b25`; the re-cloned suite
  then ran **439 passed plus 1 skipped, identical to the working checkout**, the one
  skip being the audit-log test's visible fresh-clone skip with its stated reason. Its
  mechanism is exercised by the purpose-built log test that runs everywhere.
* **Against vacuous passes:** the audit-integrity test purpose-builds its log and
  fails if nothing is checked; the source-integrity test re-hashes all 13 accepted
  documents; goldens are byte-compared; and the clone's collected count must equal the
  working checkout's exactly.

## 11. What remains, generated rather than restated

The following was the "Open" section of `AWAITING_ABHISHEK.md`, generated from
`OPEN_ITEMS.yaml` (D-088) at the time of this report; the suite fails if that file
goes stale:

* **Verify the 86-row penalty review queue (59 review-first; sanity pass first)**,
  open since 2026-08-13, at `02_data/penalty_rows/REVIEW_QUEUE_2026-08-26.yaml`. Read
  with the reconciliation: 13 disagreement sections first (crops provided), 2 the OCR
  could not read, 26 agreements. The reconciliation reduces the reading and never
  replaces the signature.
* **The D-073 layout gate's remaining legs, Adobe Acrobat plus one physical print**,
  open since 2026-08-13; the PDFium leg is done (D-085).
* **Score the blank Layer D hand-scoring sheet** *(optional)*, open since 2026-08-19;
  the self-scored pass is a worked example and disagreement baseline only.

Nothing else was open and the owner's; every ruling was ruled, and the register, not
this document, is the authority the next reader should trust. *(The second and third
items were closed on the owner's sign-off of 2026-09-04; the queue remains open.)*
