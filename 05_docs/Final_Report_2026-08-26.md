# Bail Reckoner — Final Comprehensive Report

> **SUPERSEDED 2026-08-29** by `Final_Report_2026-08-29.md`, which adds the
> cross-channel reconciliation, the sixth failure-shape instance, and the
> cold-clone verification. Kept for the record; the newer file governs.

**Date:** 2026-08-26 · **Prepared for:** Vallamalla Abhishek Prakash (team lead)
**Ordered by:** Abhishek's directive of 2026-08-26, item 10: state everything, soften nothing.

---

## 1. The one sentence that governs every other sentence

**Zero verified penalty rows exist, so the system currently computes nothing about any
real offence.** Every gate, report, filing, endpoint and test operates over synthetic
fixtures labelled as such. The engine's correctness is proved; its first real computation
happens when a human verifies the first row of the 86-row review queue — and that
verification is deliberately reserved to a human, because an agent signing rows its own
extractor drafted would collapse the independent channel and make every downstream figure
self-referential (Abhishek's item 9, standing).

## 2. Built-and-proved vs built-and-measured vs built-and-unscored

The phrase "all layers built" spans **four different states** and never appears
unqualified:

| Layer | State | What backs the claim |
|---|---|---|
| **C — engine** | **Built and PROVED** | Six gates; a test per gate and per proviso; adversarial gate-2 tests; byte-comparable golden files for every report/filing shape; Tier-1 arithmetic independently recomputed. The only layer whose correctness is proved rather than measured. |
| **A — retrieval** | **Built and MEASURED** | 2,245 sections, 8 acts, SHA+date on every chunk; Recall@k/MRR by query class (tables in `04_eval/layer_a_retrieval_2026-08-19.md`); findings below. |
| **D — precedent** | **Built and UNSCORED, over a corpus permanently labelled INCOMPLETE** | 3 of 4 judgments (Ramakrishna permanently unacquired, closed 2026-08-26); verbatim-extract-only by construction; the hand-scoring sheet of record is blank and its scoring is optional (Abhishek, 2026-08-26); the self-scored pass is not an evaluation. |
| **B — extraction** | **Seam built, NO MODEL, none possible here** | Deterministic baseline + named-human confirmation gate; P/R/F1 1.000/1.000/1.000 *measuring a deterministic gazetteer over 38 known sections in synthetic text — a floor for a future model, not charge-sheet extraction*; recall optimistic even as a floor; fine-tuning not feasible in this environment. |

Also built: REST API with honesty envelope and hash-chained append-only audit log
(truncation-detectable via out-of-log head state); server-rendered demonstrator under the
nine D-077 constraints (stack now RULED server-first, D-084); deterministic stdlib PDF
filing renderer (D-073), preview verified through PDFium (Chrome/Edge's engine) —
**remaining unverified: Adobe Acrobat rendering and a physical print** (Abhishek's,
narrowed by D-085).

## 3. Every open legal question, and its permanent conservative default

No advocate is available to this project, **permanently** — these do not close. Register:
`05_docs/Open_Questions_Register_2026-08-19.md`. Defaults, all coded and tested:

* **OLQ-1** Category-C bar: FLAG, never terminal; arithmetic shown; provision quoted;
  human review. NDPS-follows-*Badshah* expressly unsettled.
* **OLQ-2** Several offences: highest maximum governs; D-075 band shows **both**
  qualifying dates with `CONTESTED_THRESHOLD_BASIS`.
* **OLQ-3** s.479(2) vs bond route: bar reaches both; `CONTESTED`.
* **OLQ-4** POCSO: factual limb closed — no barring provision exists in the stored Act
  (`VERIFIED_ABSENT`), and *Antil*'s own Category C text does not name POCSO. **(c)/(d)
  RULED 2026-08-26**: the flag stays on the restated four-part basis implemented in
  D-054's correction; the remaining limb stays permanently open like every OLQ, but it
  awaits no ruling.
* **OLQ-5** Single FIR, multiple sections: NARROW default; `CONTESTED_479_2_SCOPE`.
* **OLQ-6** Arrest vs first remand: arrest is the clock; both shown; divergence flagged.
* **OLQ-7** Explanation's excluded days: input, default zero, never computed by the engine.
* **OLQ-8** Gate-3 set: *Antil*'s named list only, with the permanent non-exhaustive
  standing note on every report and filing.
* **OLQ-9/9a/10** Counting conventions: conservative defaults per D-047, each tested.
* **OLQ-11** Cap basis: D-066 band, `CONTESTED_CAP_BASIS`; gate 0 is never masked.
* **L-001** Per-limb keying: unnamed limb on a multi-limb section **abstains**.
* **L-002** State amendments: cannot be proved uniform from stored consolidations; the
  uniformity note stands unconditionally on every report and inside every filing's
  statutory basis.

Any `CONTESTED_*` flag hard-blocks the s.479(3) filing generator. The system has no
"ineligible" verdict (D-010); its refusals are outputs, not absences.

## 4. Every recorded divergence from the Extended Abstract

1. SQLite, not PostgreSQL+MongoDB (D-027).
2. Structured-form input at MVP; OCR out of scope (D-026).
3. Multilingual is a **recorded scope limit — RULED 2026-08-26 (D-087)**: English-only
   documents, multilingual interface chrome only. The D-030×D-073 collision is closed; a
   shaping-engine PDF path needs its own decision entry if ever revisited.
4. FAISS declined; exact numpy search (D-082).
5. Cross-encoder excluded from the shipped retrieval configuration — the EA's named final
   stage, excluded on measurement, not preference (finding below).
6. RAGAs dropped as a reasoned divergence (D-083) — the metric cannot fail here.
7. Server-rendered UI first, not React (D-084, **ruled 2026-08-26**); React addable later
   over the unchanged API.
8. No fine-tuned extraction model — infeasible here; seam + confirmation gate instead.

## 5. The failure shape — five instances

**A plausible answer where a refusal belongs:**

1. `max(1, …)` limb floor — failed detection became "one limb".
2. Counterpart ternary — fabricated a cross-code mapping.
3. TOC discard — silently dropped genuine sections (and the em-dash proxy invariant it
   exposed broke on two BNS sections).
4. Omitted unresolved extraction candidate — indistinguishable from no candidate.
5. **Cross-act collision in retrieval** — an act-less "section 303" silently answered
   with one act's section. The D-086 census promoted this from edge case to majority
   case: 510 of 723 distinct section numbers (~70%) exist in more than one act, so the
   unmitigated behaviour was **silently wrong in the majority case**. Mitigated
   2026-08-26: one labelled chunk per colliding act plus an ambiguity note, choosing
   none. Promoted into the paper's findings beside the cross-encoder and
   citation-poisoning results.

Each became a rule with a test (D-064: no convenience default on any path feeding a
statutory value).

## 6. The cross-encoder and citation-query findings (Layer A, measured)

* **Cross-encoder degradation:** NL R@10 0.921 → 0.684 (−25.7%) — the reranker demotes
  punishment sections below definitional cousins. Independently reproduces IBPS's
  degradation finding, against the EA's own named component.
* **Citation-query poisoning:** dense scores 0.000 on citation queries (embeddings cannot
  separate s.479 from s.480); through RRF the zero poisons the hybrid (citation R@10
  0.842 BM25-alone vs 0.158 hybrid). Deterministic regex router restores best-of-both.
* **Cross-act collision:** mitigated per §5; the measured figures are unchanged (the
  evaluation's citation queries all name their act).

## 7. Every claim's class — no blended figures

| Claim | Class |
|---|---|
| Gate arithmetic, thresholds, qualifying dates | **Tier 1** — independently recomputed; the only claimable accuracy |
| Golden-set legal-judgement labels | **Tier 2** — `labels not advocate-verified — indicative only` |
| Layer A Recall@k / MRR | **Retrieval measurement** — no legal judgement involved |
| Layer B P/R/F1 1.000/1.000/1.000 | **Qualified floor** — caption mandatory, recall optimistic |
| Layer D self-scores (15 R / 16 P / 5 I of 36) | **Self-scored** — the scorer's agreement with its own retrieval; **never an evaluation figure** |
| "Verified against the gazette" (s.479 text) | Document verification, character-level, provenance recorded |
| Everything about real offences | **No claim possible: zero verified rows** |

## 8. What remains — exactly three items, no rulings

The authoritative list is **generated** from `OPEN_ITEMS.yaml` (D-088) into
`AWAITING_ABHISHEK.md`; a test fails the suite if it goes stale. As of 2026-08-26 it
holds exactly three items:

1. **The 86-row review queue** (`REVIEW_QUEUE_2026-08-26.yaml`; 59 review-first; sanity
   pass = IPC 304A, IPC 379, NDPS s.20 first).
2. **Adobe Acrobat plus one physical print** of the regenerated preview (the PDFium leg
   is done; the D-073 gate is narrowed to these).
3. **The hand-scoring sheet — optional** (the self-scored pass is a worked example and
   disagreement baseline only, never an evaluation figure).

Every ruling is ruled: D-058→D-084 (server-first), OLQ-4(c)/(d) (four-part basis, in
D-054's correction), D-030×D-073→D-087 (English-only documents, multilingual chrome).

**Provenance correction (2026-08-26, on Abhishek's challenge):** the 81→77 limb-count
change is established from git — commit `aeaecc2` fixed the detector's prose rule, which
had counted an alternative *within* one limb ("…life, or with imprisonment…") as a second
limb, removing exactly one from BNS ss.331, 316, 317 and 351. That commit also **claims**
the four counts were "page-verified by eye"; the verification was never reported for
review (the three requested sections were never returned; s.351 was never on the
requested list), so the page-verification claim is **unestablished**, and all four counts
are treated as detector estimates that the review queue's page-reading corrects. The
queue header and the pinning test's docstring now say this.

**Nothing is described as complete that isn't:** the D-073 gate is narrowed, not closed;
Layer D is unscored unless and until the blank sheet is scored by its human; Tier-2
labels are permanently indicative; the paper is a successor, not a reproduction; and the
system, today, computes nothing real.
