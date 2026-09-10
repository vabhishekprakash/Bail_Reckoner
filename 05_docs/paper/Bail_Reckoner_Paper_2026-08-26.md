# AI-Powered Bail Reckoner: Computing Statutory Entitlement to Release under Section 479 BNSS 2023

**Problem statement SIH1702 (Ministry of Law & Justice, Government of India) · Institute
reference MLRS24-169 · Final-year B.Tech major project, CSE (AI & ML), Marri Laxman Reddy
Institute of Technology and Management, Hyderabad, 2026-27.**

**Team:** Vallamalla Abhishek Prakash (lead) · Revuru Arya · Modhumpally Arvind · Boru Vimala.

> **PROVENANCE, READ FIRST.** This document is a regeneration, not a reproduction. The
> project's earlier paper was generated in an external chat session and never brought
> under version control (recorded as a process defect in the Implementation Status
> Ledger); its prose is not recoverable from this repository. This successor was
> authored 2026-08-26 from the repository itself (the decision log, the Open Questions
> Register, `SOURCES.md`, the evaluation reports in `04_eval/`, and the Implementation
> Status Ledger) on the lead's direction, and is versioned in git with its SHA-256
> recorded in the ledger. If a copy of the original paper circulates, the two agree in
> substance and diverge in wording; this file governs for the project's claims. Every
> figure below carries its claim class (see Claim classes); no blended accuracy figure
> appears anywhere in this document.

---

## Abstract

Undertrial prisoners in India hold a statutory entitlement to release once their custody
crosses a fraction of the maximum sentence for the offence charged: one-half, or
one-third for a first-time offender, under Section 479 of the Bharatiya Nagarik Suraksha
Sanhita, 2023. The entitlement is arithmetic, but going unclaimed in practice is the
premise on which problem statement SIH1702 was issued. Computing it requires the
offence's maximum sentence, the custody duration, several statutory exclusions and bars,
and an application the jail Superintendent is obliged to make. The Bail Reckoner
computes this entitlement deterministically, shows every step of the arithmetic, and
cites the provision behind each step. It does not predict bail outcomes and does not
score judicial discretion; it is a decision-support aid for legal-aid providers,
Undertrial Review Committees and jail authorities, never an autonomous decision-maker.
The system is built as four layers around a pure, model-free decision engine (Layer C)
whose correctness is proved by golden-file tests rather than measured. The retrieval
(A), extraction (B) and precedent (D) layers serve research and input surfaces and are
strictly excluded from the decision path, a boundary enforced by an import-level test.
We report the layers' four distinct completion states honestly, along with several
original empirical findings, including a cross-encoder reranker destroying 25.7% of
correct retrieval results and dense embeddings scoring 0.000 on citation-style queries.
The system's central design commitment: where the law is unsettled or a value is
undetected, it refuses or flags for human review. It never substitutes a plausible
answer.

---

## I. Introduction

India's prisons hold a large undertrial population, documented year on year by the
National Crime Records Bureau's *Prison Statistics India* series, and Section 479 BNSS
2023 (the successor to s.436A CrPC) entitles many of them to release on completing a
defined fraction of the maximum sentence they could receive if convicted. The provision
requires no judicial discretion at the entitlement stage: given the offence's statutory
maximum, the custody undergone, and a small set of statutory tests, the entitlement is a
computation. Yet the computation is not being done at scale. The project's Extended
Abstract cites PSI 2024 (figures as on 31 December 2024); the specific numbers are in
that document and are not restated here, because this regeneration only asserts what the
repository verifies.

Problem statement SIH1702 asks for an AI-powered facilitator for this computation. The
scope is fixed by the Ministry's problem statement and is not altered here (project
constraint C6).

**What the system is not.** It does not predict bail outcomes (D-012) and does not model
or score judicial discretion (D-009: discretionary factors such as flight risk are
surfaced as an unweighted verbatim checklist for a human, never scored). It has no
"ineligible" output state (D-010); its two verdicts are `ENTITLEMENT_ESTABLISHED` and
`NO_ENTITLEMENT_IDENTIFIED — HUMAN REVIEW REQUIRED`, because a false "eligible" is
caught by the court while a false "ineligible" silently keeps a person in custody, and
nobody appeals a machine's silence. Asymmetric error costs demand asymmetric design.

## II. Related work and positioning

* **HLDC** (Findings of ACL 2022) and **IBPS** (arXiv:2508.07592) predict bail
  *outcomes* from case text. This project is deliberately distinct: it computes a
  statutory *entitlement* (D-012). Outcome prediction learns judicial behaviour and
  inherits its disparities; entitlement computation restates the statute's own
  arithmetic.
* **ICJS, e-Prisons/BOMS, FASTER, UTRCs and the e-Courts stack** transmit records and
  orders between institutions. None of them computes bail entitlement under Section
  479; that reasoning layer is this project's contribution. The claim that "no digital
  tool exists" is false and is never made (D-011).
* IBPS's finding that naive retrieval augmentation degrades a baseline is independently
  reproduced by this project's cross-encoder measurement (section VII).

## III. Statutory ground truth

The engine encodes Section 479 BNSS 2023 (Act 46 of 2023) as verified against the
official gazette (Gazette of India Extraordinary, Part II—Sec. 1, No. 54, 25 Dec 2023;
cross-checked character-identical against India Code as on 2025-10-06). Verification was
a gate for encoding (D-008), and it paid for itself: the gazette text contains an
Explanation to s.479(1), excluding detention caused by the accused's own delay from the
computation, that was absent from every pre-verification project document. A system
encoded from secondary sources would have missed a provision that directly modifies the
custody arithmetic. The Explanation is handled as an `excluded_days` input, default
zero, and is never computed by the engine, because what counts as accused-caused delay
is a judicial determination (OLQ-7).

The engine implements six gates, in a fixed order (D-033/D-034):

| # | Gate | Kind | Provision |
|---|---|---|---|
| 0 | Custody ≥ maximum period prescribed? | ALWAYS COMPUTED FIRST → `DETAINED_BEYOND_MAXIMUM`, never masked by any later gate | s.479(1) third proviso |
| 1 | Death or life imprisonment prescribed? | BAR | s.479(1) main clause |
| 2 | Multiple offences or cases pending? | BAR; scope configurable, default NARROW; a single FIR with multiple sections → `CONTESTED`, human review (D-025) | s.479(2) |
| 3 | Special-statute bail restriction? | FLAG (`SPECIAL_STATUTE_TEST_REQUIRED`); never a terminal bar (D-033); fires on offence-in-scope, not statute membership (D-074) | *Satender Kumar Antil* Category C |
| 4 | First-time offender? | SELECTS THE FRACTION (one-third on bond against one-half on bail); not a bar | s.479(1) first proviso |
| 5 | Custody ≥ applicable threshold? | TEST | s.479(1) plus third proviso |

Gates 0, 1 and 5 compute over *pending* offences only (D-072: s.479(1) ties the period
to an offence under investigation, inquiry or trial, and a concluded case is under none
of those; letting a concluded case's maximum leak into the arithmetic was shown to
suppress the gate-0 cap alarm). Where the governing maximum is itself contested
(several offences, or the cap's basis under OLQ-11), the engine computes a band and
emits dual qualifying dates with a `CONTESTED_*` flag (D-066, D-075), and any
`CONTESTED_*` flag hard-blocks the s.479(3) filing generator.

## IV. Architecture: four layers around a pure core

```
Layer A (retrieval)   Layer B (extraction seam)   Layer D (precedent)
        \                     |                        /
         [research & input surfaces — NEVER the decision path]
                              |
                    human confirmation gate
                              |
                    Layer C — pure engine  ->  reports, s.479(3) filing, API, audit
```

Layer C is the defensible core: deterministic functions over typed inputs, with no
model, no network and no file access in the decision path. The boundary is not a
convention but a test (`test_engine_boundary.py`) that fails if the engine package
imports retrieval, extraction, precedent, or any model dependency. Every engine
function implementing a provision cites it by sub-section in its docstring. Every
output carries `statute_version`, `law_in_force_on`, `inputs_hash`, `rules_fired[]`,
and an empty `reviewed_by` field that stays empty until a human signs.

Statutory parameters are versioned data (D-055): the decision table is YAML with a
content hash that stamps every output, and report and filing language lives in
versioned YAML with loaders that fail on missing coverage in either direction.

**Outputs.** A section-wise report (offence → section → max sentence → custody →
fraction served → threshold → status) in byte-comparable text, and a s.479(3)
application generator with four hard refusal conditions (no entitlement; case list
unverified; any `CONTESTED_*` flag; the one-third route without verified
prior-conviction status). Blanks are never auto-filled, statutory quotes are drawn only
from the versioned table, and the PDF renderer is deterministic, standard-library-only
code (D-073: no timestamps, byte-identical re-renders). Three standing lines travel on
every report and filing: the State-amendment uniformity note (L-002), the
special-statute set note (*Antil*'s Category C list "is itself non-exhaustive"), and a
source-inventory line (13 accepted documents, SHA-256 verified by a recurring test).

**API and interface.** A REST API (FastAPI, D-076/D-079) exposes reports, filings and
the extraction seam, with a pydantic `extra="forbid"` contract that rejects any attempt
to smuggle maxima past the server-side resolution (D-060), an honesty envelope on every
response (`verified_row_count`, currently with the unmissable warning that zero
verified rows exist), and an append-only hash-chained audit log whose head state is
kept outside the log so truncation is detectable. The interface is server-rendered
first, ruled on 2026-08-26 (D-084) as a recorded divergence from the Extended
Abstract's React line; the API contract keeps a React client addable later without
server changes. Nine hard UI constraints (D-077) include: no status colours or icons in
either direction, full verdict strings never truncated, refusals displayed and never
omitted, and affirmations never pre-ticked.

## V. Data: the statutory-penalty database

Every row requires `source`, `verified_against` and `verified_on`. A row without
provenance does not enter the database, and an uncovered offence returns
`OFFENCE_NOT_IN_DATABASE`, never a guess. Rows are keyed per punishment limb (D-061)
because a section's sub-sections carry different maxima (BNS s.303(2): three years,
with a separate one-to-five-year limb on subsequent conviction), and an unnamed limb on
a multi-limb section abstains rather than picking one.

**As of this writing, zero verified rows exist.** The 86-row consolidated review queue
(59 rows in the review-first set) awaits human verification against the stored gazette
and India Code PDFs. This is by design and stated everywhere the system speaks: an
agent verifying rows its own extractor drafted would collapse the independent channel
the review exists to provide, and every downstream figure would become
self-referential. Until rows are verified, the system computes nothing about any real
offence, and every demonstration runs on synthetic fixtures labelled as such (a fixture
citing a real section may only exist once that section has a verified row; violations
are caught by a fixture-convention test).

To reduce the reviewer's exposure to extraction artefacts, the queue carries a
cross-channel reconciliation (D-089, 2026-08-29): every cited page was re-read by a
second, independent channel, rasterised via PDFium and read by OCR, never touching the
PDF text layer, so the text channel's documented failure modes cannot recur in it. The
two channels' mechanically extracted facts (term maxima, mandatory minima, life and
death mentions, limb count) were compared per section. Disagreements, listed first with
cropped page images, mark pages where the machines cannot both be right. The agreement
rate's claim class is cross-channel agreement measurement, not verification and not
accuracy, and no machine reading from either channel enters the database (D-046).

Sources are governed by `01_law/SOURCES.md`: 13 accepted documents (10 statutes, 3
judgments), each with its acquisition-time SHA-256 re-verified by a recurring integrity
test, plus a rejected-sources list that includes an un-amended UAPA text (whose use
would have produced a false `VERIFIED_ABSENT` for s.43-D(5)), an IPC PDF covering only
ss.1-120, a pre-2013 IPC text, and a Law Commission report mislabelled as the NDPS Act.
Three official-looking sources were defective, and two had actively misleading
filenames. The project's rule: a filename is not provenance. Open the file before
believing its label.

## VI. Layer C verification (claim class: Tier 1)

Layer C's golden set is two-tiered (project constraint on labelling). Tier 1 is
arithmetic-verifiable: given a maximum read off the bare act and a custody duration,
the threshold is division, verified by independent recomputation (one path by hand, one
by script, disagreements adjudicated against the bare act). Tier 2 (offence
classification, s.479(2) applicability, first-offender status on a real record)
requires legal judgement, and no advocate or law-faculty reviewer is available to this
project, permanently. Tier 2 labels therefore measure agreement with the labeller, are
captioned `labels not advocate-verified — indicative only`, and are never blended with
Tier 1. The full test suite stands at 439 passing tests plus one visible, reasoned
skip, with a test per gate, a test per proviso, adversarial tests on gate 2, and
byte-comparable golden files for every report and filing shape.

## VII. Layer A: retrieval (claim class: retrieval measurement, no legal judgement)

The corpus is 2,245 sections across 8 acts (IPC, BNS, BNSS, NDPS, PMLA, UAPA, Companies
Act, POCSO), chunked hierarchy-aware by section, every chunk carrying its source
document's acquisition SHA-256 and as-on date. A chunk is citable to a verified
document version or it is not in the corpus. Retrieval is BM25 (rank_bm25, D-080) plus
dense embeddings (sentence-transformers MiniLM, D-081) fused by reciprocal-rank fusion,
with a cross-encoder reranker (ms-marco-MiniLM) available. FAISS was declined (D-082, a
recorded divergence): exact numpy search is complete recall at this scale. Evaluation
ran 38 natural-language and 38 citation-style queries derived from the page-verified
seed sections, with Recall@k and MRR reported by query class and never blended:

| Configuration | Recall@1 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|
| [NL] BM25 only | 0.342 | 0.763 | 0.842 | 0.511 |
| [NL] Dense only | 0.342 | 0.605 | 0.737 | 0.457 |
| [NL] Hybrid (RRF) | 0.368 | 0.816 | 0.921 | 0.530 |
| [NL] Hybrid + cross-encoder | 0.474 | 0.658 | 0.684 | 0.543 |
| [NL] Routed (deterministic) | 0.368 | 0.816 | 0.921 | 0.530 |
| [CITATION] BM25 only | 0.132 | 0.737 | 0.842 | 0.363 |
| [CITATION] Dense only | 0.000 | 0.000 | 0.000 | 0.000 |
| [CITATION] Hybrid (RRF) | 0.000 | 0.026 | 0.158 | 0.019 |
| [CITATION] Hybrid + cross-encoder | 0.053 | 0.474 | 0.684 | 0.250 |
| [CITATION] Routed (deterministic) | 0.132 | 0.737 | 0.842 | 0.363 |

**Finding 1: the cross-encoder destroys a quarter of the correct results** on
natural-language queries, with R@10 falling 0.921 → 0.684 (−25.7%) against the plain
hybrid. The mechanism: the reranker demotes punishment sections below their
definitional cousins (asked for "punishment for cheating", it prefers the section
*defining* cheating). This independently reproduces IBPS's finding that naive retrieval
augmentation can degrade a baseline, here against the Extended Abstract's own named
final stage, which is therefore excluded from the shipped configuration. A measured
divergence, not a preference.

**Finding 2: dense retrieval scores 0.000 on citation queries.** Embeddings cannot
separate "section 479" from "section 480", and through rank fusion the zero poisons the
hybrid (citation R@10 of 0.842 for BM25 alone against 0.158 for the hybrid). The
mitigation is deterministic: a regex router sends citation-shaped queries to the
lexical leg alone, and the routed configuration holds the best figures of both classes
simultaneously.

**Finding 3: cross-act collision is the majority case, not an edge case** (census,
D-086). 510 of 723 distinct section numbers in the corpus, roughly 70%, exist in more
than one act ("section 303" exists in four: IPC, BNS, BNSS, Companies Act). An act-less
citation query is therefore ambiguous in the majority case, and the unmitigated
behaviour of silently ranking one act's section as the answer was silently wrong in the
majority case, not occasionally. This is the fifth recorded instance of the project's
central failure shape, a plausible answer where a refusal belongs (section XI), and it
stands beside Findings 1 and 2 as an original empirical result. Mitigated 2026-08-26
(D-086): an act-less citation query whose number collides returns one labelled chunk
per act plus an explicit ambiguity note, choosing none.

## VIII. Layer D: precedent (claim class: none claimable; see text)

Verbatim-extract-only by construction: the extract type has no summary field, so a
hallucinated citation is unrepresentable rather than merely discouraged. The corpus
holds 3 of the 4 project-cited judgments, acquired under the same discipline as
statutes (SHA-256, integrity-covered): *Satender Kumar Antil v. CBI* (at this date a
judiciary-hosted mirror, with its Indian Kanoon print lineage stated), with *Badshah
Majid Malik v. ED* and *Union of India v. K.A. Najeeb* both from the Supreme Court's
own API, primary. *K. Ramakrishna v. Assistant Director, ED* (Karnataka HC) failed
acquisition at a primary source (a captcha-gated portal) and is permanently unacquired
(closed 2026-08-26): no aggregator copy is substituted, and every citation of it is
secondary-sourced and says so. Every Layer D result carries a
`CORPUS INCOMPLETE: 3 of 4` line.

Primary-text acquisition produced two corrections secondary sources had gotten wrong.
The operative *Badshah* date is the Order of 18 October 2024, not the "27 December
2024" the project's records had carried. And *Antil*'s own Category C text does not
name POCSO; its four named statutes end with "etc.", making the list non-exhaustive,
which is now a standing note on every report and filing.

RAGAs evaluation was dropped as a reasoned divergence (D-083): Layer D generates
nothing, so faithfulness holds by construction and the metric cannot fail. The live
property is retrieval relevance, measured by a hand-scoring sheet (12 queries by 3
extracts) that awaits its human scorer. A self-scored pass exists
(`04_eval/layer_d_handscore_SELFSCORED_2026-08-26.md`) and is labelled throughout as
measuring the scorer's own agreement with its own retrieval. It is not an evaluation
figure and is never reported as one, including here.

## IX. Layer B: extraction seam (claim class: qualified floor; see caption)

A seam, not a model. Candidate offences are extracted as unconfirmed-by-type objects
(span, snippet, and a `regime` that stays `None` when the enactment is unnamed, never
guessed), and nothing extracted reaches the engine without a named human's confirmation
against the shown source text. Fine-tuning an extraction model is not feasible in this
environment (no GPU, and no training corpus that would be lawful to hold; see section
X), stated plainly rather than worked around.

The deterministic baseline (citation patterns including chained forms such as
"Sections 341 and 351 IPC" and "u/s 379, 411 and 420", plus a 38-section offence-name
gazetteer) measures P/R/F1 of 1.000/1.000/1.000, a figure that must never travel
without this caption: it measures a deterministic gazetteer over 38 known sections in
synthetic text, a floor for a future model, not charge-sheet extraction, and not the
capability the Extended Abstract promises. The synthetic corpus does not represent real
charge-sheet drafting (longer chains, mixed regimes, vernacular forms, OCR noise), so
even as a floor the recall is optimistic.

## X. Data protection and ethics

No real accused person's data exists anywhere in this project. Fixtures are synthetic
and labelled as such in file headers, and the data-protection discipline extends to
transport: the extraction endpoint never persists or logs submitted text (the audit log
records length and SHA-256 only, pinned by test). There is no web scraping of case
records; judgments were acquired from official hosting only. Discretionary factors are
never scored (D-009), which also removes the principal disparate-impact surface. Every
generated report carries an empty `Legally reviewed by:` field; the system is a
facilitator, and the empty line is the architecture saying so.

## XI. The recurring failure shape, named

Six times during construction, the same defect appeared in different clothes: a
plausible answer where a refusal belongs.

1. A `max(1, ...)` floor that turned a failed limb detection into "one limb".
2. A counterpart ternary that fabricated a cross-code mapping when none existed.
3. A table-of-contents discard that silently dropped genuine sections (and, once fixed
   structurally, exposed that an em-dash typography test was a proxy invariant that
   broke on two BNS sections).
4. An omitted unresolved candidate in the extraction view: a candidate the system could
   not classify was simply not shown, indistinguishable from no candidate.
5. Cross-act collision in retrieval (section VII, Finding 3): an act-less "section 303"
   silently answered with one act's section, when the census showed the ambiguity is
   the majority case (about 70% of section numbers collide), so the plausible answer
   was wrong most of the time, not occasionally.
6. A `max(0, ...)` floor in the custody arithmetic, found by a directed adversarial
   self-audit (2026-08-29) hunting precisely this shape: self-contradictory inputs
   (more break or excluded days than days detained) were floored into a plausible
   effective custody of zero instead of being refused. Zero custody *under*-claims,
   the dangerous direction under D-010's asymmetry. The same audit hardened three
   silent paths in the precedent-corpus builder (a missing judgment, a missing
   provenance hash, and an empty page extraction were all absorbed silently while the
   corpus-status line kept asserting completeness) and caught a wrong page-index
   convention in the review queue's own instructions, off by one page.

Each instance was converted into a rule with a test (the fifth through D-086; the
sixth through the custody refusal, the corpus-builder refusals and the corrected queue
header, each with its pinning test). The project's standing rule (D-064): no
convenience default on any path feeding a statutory value. A zero, None or absent
result there is a failed detection to report, never a value to substitute.

## XII. Open legal questions (all permanently open; conservative default coded per question)

No advocate is available to this project, permanently, so these questions do not
close. Each is coded to a conservative default that surfaces the uncertainty rather
than resolving it. The authoritative register is
`05_docs/Open_Questions_Register_2026-08-19.md`; the load-bearing entries:

| OLQ | Question | Coded default |
|---|---|---|
| 1 | Does a Category C bar extinguish or merely qualify the s.479 entitlement (and does NDPS follow *Badshah*)? | Gate 3 is a FLAG, never a terminal bar; arithmetic shown in full; provision quoted; human review |
| 2 | Which maximum governs with several offences charged? | The highest (longest threshold); a band with dual qualifying dates and `CONTESTED_THRESHOLD_BASIS` (D-075) |
| 3 | Does the s.479(2) bar reach the first-proviso bond route? | The bar reaches both routes; `CONTESTED` flag |
| 4 | Which POCSO provision is the Category C bar? | Factual limb closed: none exists in the stored Act (`VERIFIED_ABSENT`), and *Antil* itself does not name POCSO. Basis ruled 2026-08-26: the flag stays on the four-part basis of D-054's correction (secondary placement; judgment silent; no twin-condition bar; ss.29-30 presumptions); the remaining limb stays open like every OLQ but awaits no ruling |
| 5 | Does a single FIR with multiple sections trigger s.479(2)? | NARROW default; `CONTESTED_479_2_SCOPE`, human review (D-025) |
| 6 | Threshold from arrest or first remand? | Arrest is the primary clock; both captured, divergence flagged (D-028) |
| 7 | What is "delay caused by the accused" (the Explanation)? | An `excluded_days` input, default zero, never computed by the engine |
| 8 | Which statutes belong in gate 3's set? | *Antil* Category C's named list only, with the standing non-exhaustive note (D-054 as corrected) |
| 9, 9a, 10 | Day-counting conventions; the cap for carve-out offences; part-month handling | Conservative conventions per D-047, each recorded in the register with its test |
| 11 | Does the cap measure per offence or against the governing maximum? | A band with `CONTESTED_CAP_BASIS` (D-066); gate 0 is never masked |

Two structural legal questions (the L-series) precede schema. L-001 asks whether the
statute supports per-limb keying at all, which is why the review abstains on unnamed
limbs. L-002 concerns State amendments: the stored consolidations cannot prove
State-law uniformity, hence the standing uniformity note on every report and filing.

## XIII. Recorded divergences from the Extended Abstract

Stated openly, per the D-027 pattern. The abstract is not retro-edited; the record is:

1. SQLite, not PostgreSQL plus MongoDB (D-027). The deployment target is a single
   district-office machine, and the schema is written for mechanical migration.
2. Structured form input at MVP, with OCR out of scope (D-026); a recorded limitation.
3. Multilingual is a recorded scope limit, ruled 2026-08-26 (D-087, closing the
   D-030 and D-073 collision): every generated document is English, and interface
   chrome may localise. Devanagari or Telugu documents would need a text-shaping
   engine, never a font swap, under a future decision entry of their own.
4. FAISS declined (D-082); exact numpy search gives complete recall at corpus scale.
5. The cross-encoder is excluded from the shipped retrieval configuration on measured
   harm (section VII, Finding 1). It was the abstract's named final stage.
6. RAGAs dropped as a reasoned divergence (D-083); the metric cannot fail here.
7. Server-rendered UI first, not React (D-084, ruled 2026-08-26); a React client is
   addable later over the unchanged API.
8. No fine-tuned extraction model (section IX), which is not feasible in this
   environment; the seam and confirmation gate ship instead, with the qualified floor
   stated.

## XIV. Status: the four states of "built" (the paper's Table IV)

"All layers built" is true only across four different meanings of built, and the
phrase never appears unqualified:

| Layer | State |
|---|---|
| C (engine) | **Complete and verified**: proved by golden tests; the only layer whose correctness is proved rather than measured |
| A (retrieval) | **Complete and measured**: figures in section VII, by query class |
| D (precedent) | **Built over a corpus permanently labelled INCOMPLETE, and unscored**: 3 of 4 judgments; hand-scoring awaits its human scorer |
| B (extraction) | **Seam built, no model, none possible here**: a deterministic floor with a mandatory caption, plus the human confirmation gate |

And above all of it: zero verified penalty rows exist, so the system currently
computes nothing about any real offence. The arithmetic engine is proved correct over
synthetic fixtures; its first real computation happens when a human verifies the first
row.

## XV. Claim classes

Every number in this project belongs to exactly one class, and classes are never
blended:

| Class | What it can claim | Where it appears |
|---|---|---|
| **Tier 1** | Arithmetic correctness, independently recomputed | Layer C golden set |
| **Tier 2** | Agreement with a non-advocate labeller; indicative only | Golden-set legal-judgement labels |
| **Retrieval measurement** | Recall@k and MRR of a search component; no legal judgement | Layer A (section VII) |
| **Qualified floor** | A deterministic baseline's lower bound, caption mandatory | Layer B P/R/F1 |
| **Self-scored** | The scorer's agreement with its own system; never an evaluation figure | Layer D self-scored sheet |
| **Cross-channel agreement** | Two independent machine channels (text layer against OCR) agreeing on mechanically extracted facts; not verification and not accuracy, since both can be wrong together | The queue reconciliation (`04_eval/cross_channel_reconciliation_2026-08-29.md`) |

## XVI. Conclusion

The Bail Reckoner's contribution is not a model. It is an architecture of honesty
around a provable computation: a pure engine whose every step cites its provision,
refusal and flagging wherever the law is unsettled or a value undetected, provenance on
every statutory fact, and evaluation that names what each number can and cannot claim.
The system's most important outputs include its refusals, and its most important
empirical findings are the ones that argue against its own initially planned
components.

---

*Regenerated 2026-08-26 from the repository at the commit recorded in the project's
session log; the SHA-256 of this file is recorded in the Implementation Status Ledger.
Successor to the chat-session paper; supersedes it for all project claims. Prose
restyled 2026-09-10 for the public release with every fact, figure and date unchanged;
the ledger carries the hash supersession chain.*
