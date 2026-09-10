# Implementation Status Ledger: mirror of the paper's Table IV

**Purpose (the owner's item 9, 2026-08-19):** the project paper's Table IV records
layer status, and Layers A, B, D, the API and the interface were recorded there as
*Not started*. The original chat-session paper was never in this repository, so it
could not be updated from here. This ledger is the single source for that table:
update the paper FROM this file, and record here when that happens.

| Component | Paper says | Actual status | As of |
|---|---|---|---|
| Layer C (engine, six gates) | — | **Built**: 6 gates, D-072 pending-only, bands D-066/D-075 | 2026-08-19 |
| Reports + s.479(3) filing | — | **Built**: text plus deterministic PDF, golden-tested | 2026-08-19 |
| REST API | Not started | **Built**: /v1/meta, /v1/reports, /v1/applications (+pdf), /v1/extract; honesty envelope; hash-chained audit log (D-076); engine refusals reach callers as 422s carrying their reason, never reason-less 500s (D-092) | 2026-09-02 |
| Interface | Not started | **Built, server-rendered** (D-077 constraints; stack ruled by D-084, an Extended Abstract divergence, with React optional later over the same API). Interface-chrome i18n mechanism in place: English complete, Hindi and Telugu slots EMPTY awaiting a human-reviewed translation and never machine-filled (D-090, council-reviewed; form ratified by the owner 2026-09-04); documents are English-only in every language setting (D-087) | 2026-09-02 |
| Layer A (retrieval) | Not started | **Built**: 2,245-section corpus (8 acts, SHA and date per chunk), BM25 plus dense hybrid, cross-encoder rerank; Recall@k and MRR report in 04_eval/ | 2026-08-19 |
| Layer D (precedent) | Not started | **Built over 3 of 4 judgments, all three now Supreme Court API primaries** (Antil upgraded from a judiciary mirror 2026-09-02, D-091, ratified 2026-09-04; verbatim-extract-only by construction; corpus-incomplete label on every result; Ramakrishna permanently unacquired). Hand-score sheet of record regenerated from the primary corpus: `04_eval/layer_d_handscore_2026-09-02.md`; scoring optional | 2026-09-02 |
| Layer B (extraction) | Not started | **Seam built, no model**: deterministic baseline plus a human confirmation gate; P/R/F1 of 1.000/1.000/1.000 *measuring a deterministic gazetteer over 38 known sections in synthetic text, a floor for a future model rather than charge-sheet extraction*; fine-tuning not feasible here | 2026-08-19 |
| Verified penalty rows | — | **0**. The consolidated review queue (86 rows, 59 review-first; REVIEW_QUEUE_2026-08-26.yaml) is the owner's. *Figure corrected 2026-08-26: the earlier "31" added 22 priority sections to 9 NDPS rows, mixing units. In rows: 59 review-first = 50 seed priority + 9 NDPS; 86 total = 77 seed + 9 NDPS.* | 2026-08-26 |
| PDF viewer validation | — | **Closed** (2026-09-04): the PDFium leg was machine-verified (D-085, both pages inspected at 144 dpi); the Acrobat and physical-print legs closed on the owner's sign-off of 2026-09-04, and the record states plainly that those two legs rest on his statement rather than machine verification | 2026-09-04 |

**Standing caveats that travel with any status claim:** zero verified penalty rows
exist, so every computation abstains or runs on labelled synthetic fixtures; no
advocate review is available, permanently (see the Open Questions Register); and Layer
A's metrics are retrieval measurements with no legal judgement involved, never to be
blended with Tier 2 figures.


## Findings that belong in the paper (not only in eval files)

1. **Cross-encoder degradation (an original empirical result).** On natural-language
   queries the cross-encoder destroys a quarter of the correct results hybrid
   retrieval had already found: R@10 falls 0.921 → 0.684 (−25.7%). The mechanism is
   punishment sections demoted below definitional cousins. This independently
   reproduces the IBPS finding that naive retrieval augmentation degrades a baseline.
2. **Adjacent-section confusion, measured.** Dense retrieval scores 0.000 on
   citation-style queries ("section 479 BNSS") because embeddings cannot separate
   s.479 from s.480, and the zero poisons the hybrid through rank fusion (citation
   R@10 of 0.842 for BM25 alone against 0.158 for the hybrid). Mitigated
   deterministically: a regex router sends citation-shaped queries to the lexical leg,
   and the routed configuration holds the best figures of both classes. A second
   confusion, cross-act collision ("section 303" exists in four acts; 510 of 723
   distinct section numbers collide), was recorded unmitigated on 2026-08-19 and
   **mitigated 2026-08-26 (D-086)**: an act-less colliding citation query now returns
   one labelled chunk per act and an ambiguity note, choosing none.
3. **The paper itself.** Generated in a chat session and never directed into the repo
   (the owner's record). The intake process, once supplied: store under 05_docs/,
   SHA-256 into SOURCES.md, covered by the integrity test, future versions diffable.
   Known-stale content to fix on intake: Table IV's Not-started rows (above), Section
   IX's "planned" retrieval evaluation (now measured), the extraction-defects table
   (grown), the FAISS stack line (D-082 divergence), and the Badshah date (18 Oct
   2024, not 27 Dec). **Regenerated 2026-08-26 on the owner's direction**: a successor
   paper authored from the repository (not a reproduction, since the original's prose
   is unrecoverable) lives at `05_docs/paper/Bail_Reckoner_Paper_2026-08-26.md`, under
   version control. Current SHA-256
   `038a84c2bfb54134b029bf515dab425dda029c3e223363149490192a184d9f18`
   (rev. 2026-09-10: prose restyled for the public release, every fact, figure and
   date unchanged; supersedes `f5cbba4f…ac71`, `6d952e84…6394` and `5cef3494…3d6b90`).
   It carries the four states as its Table IV, every recorded Extended Abstract
   divergence, the Layer A findings, and a claim-class table, and it states that it
   supersedes the chat-session paper for all project claims. If a circulated copy of
   the original ever surfaces, diff before relying on either.


## "All layers built" spans four different states: flag for the paper

The phrase must never appear unqualified. As of 2026-08-19:

* **Layer C, complete and verified**: six gates, golden-tested, provable arithmetic;
  the one layer whose correctness is proved rather than measured.
* **Layer A, complete and measured**: 2,245-section corpus, hybrid retrieval, Recall@k
  and MRR reported by query class, with the cross-encoder and adjacency findings.
* **Layer D, built over a corpus permanently labelled INCOMPLETE, and unscored**: 3 of
  4 judgments (Ramakrishna permanently unacquired); the hand-scoring sheet's scoring
  is optional (the owner, 2026-08-26; tracked in OPEN_ITEMS.yaml); every output
  carries the corpus-status line.
* **Layer B, seam built with NO MODEL, and none possible in this environment**: a
  deterministic baseline plus the human confirmation gate. The P/R/F1 figures measure
  a deterministic gazetteer over 38 known sections in synthetic text, a floor for a
  future model rather than charge-sheet extraction, and not the capability the
  Extended Abstract promises. The synthetic corpus does not represent real
  charge-sheet drafting, so recall is optimistic even as a floor.

The paper's next revision must carry these four states, not a single "built" row each.
