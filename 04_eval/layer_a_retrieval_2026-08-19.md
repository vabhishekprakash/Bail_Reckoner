# Layer A retrieval evaluation — 2026-08-19

**Claim class: retrieval measurement, no legal judgement involved.** The query set
derives from the 38 seed sections (offence label -> its own page-verified section).
This figure is DISTINCT from any Tier-2 number and must never be blended with one.

Corpus: 2245 statutory sections from the accepted primary acts, each
chunk carrying its source SHA-256 and as-on date.

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

## Misses at k=10 — [NL] BM25 only
* 'punishment for theft' -> expected BNS 2023 s.303
* 'punishment for murder' -> expected BNS 2023 s.103
* 'punishment for causing death by negligence' -> expected BNS 2023 s.106
* 'punishment for wrongful restraint' -> expected BNS 2023 s.126
* 'punishment for cheating' -> expected IPC 1860 s.420
* 'punishment for cheating' -> expected BNS 2023 s.318

## Misses at k=10 — [NL] Dense only
* 'punishment for theft' -> expected IPC 1860 s.379
* 'punishment for theft' -> expected BNS 2023 s.303
* 'punishment for causing death by negligence' -> expected IPC 1860 s.304A
* 'punishment for causing death by negligence' -> expected BNS 2023 s.106
* 'punishment for attempt to murder' -> expected BNS 2023 s.109
* 'punishment for voluntarily causing grievous hurt' -> expected BNS 2023 s.117
* 'punishment for wrongful restraint' -> expected BNS 2023 s.126
* 'punishment for dishonestly receiving stolen property' -> expected BNS 2023 s.317
* 'punishment for house-trespass' -> expected BNS 2023 s.331
* 'punishment for criminal intimidation' -> expected BNS 2023 s.351

## Misses at k=10 — [NL] Hybrid (RRF)
* 'punishment for theft' -> expected BNS 2023 s.303
* 'punishment for causing death by negligence' -> expected BNS 2023 s.106
* 'punishment for wrongful restraint' -> expected BNS 2023 s.126

## Misses at k=10 — [NL] Hybrid + cross-encoder
* 'punishment for theft' -> expected BNS 2023 s.303
* 'punishment for causing death by negligence' -> expected BNS 2023 s.106
* 'punishment for voluntarily causing grievous hurt' -> expected BNS 2023 s.117
* 'punishment for wrongful restraint' -> expected BNS 2023 s.126
* 'punishment for robbery' -> expected BNS 2023 s.309
* 'punishment for criminal breach of trust' -> expected BNS 2023 s.316
* 'punishment for cheating' -> expected BNS 2023 s.318
* 'punishment for dishonestly receiving stolen property' -> expected BNS 2023 s.317
* 'punishment for mischief' -> expected BNS 2023 s.324
* 'punishment for house-trespass' -> expected BNS 2023 s.331
* 'punishment for criminal intimidation' -> expected BNS 2023 s.351
* 'punishment for kidnapping' -> expected BNS 2023 s.137

## Misses at k=10 — [NL] Routed (deterministic)
* 'punishment for theft' -> expected BNS 2023 s.303
* 'punishment for causing death by negligence' -> expected BNS 2023 s.106
* 'punishment for wrongful restraint' -> expected BNS 2023 s.126

## Misses at k=10 — [CITATION] BM25 only
* 'section 303 BNS' -> expected BNS 2023 s.303
* 'section 117 BNS' -> expected BNS 2023 s.117
* 'section 309 BNS' -> expected BNS 2023 s.309
* 'section 316 BNS' -> expected BNS 2023 s.316
* 'section 324 BNS' -> expected BNS 2023 s.324
* 'section 331 BNS' -> expected BNS 2023 s.331

## Misses at k=10 — [CITATION] Dense only
* 'section 379 IPC' -> expected IPC 1860 s.379
* 'section 303 BNS' -> expected BNS 2023 s.303
* 'section 302 IPC' -> expected IPC 1860 s.302
* 'section 103 BNS' -> expected BNS 2023 s.103
* 'section 304 IPC' -> expected IPC 1860 s.304
* 'section 105 BNS' -> expected BNS 2023 s.105
* 'section 304A IPC' -> expected IPC 1860 s.304A
* 'section 106 BNS' -> expected BNS 2023 s.106
* 'section 307 IPC' -> expected IPC 1860 s.307
* 'section 109 BNS' -> expected BNS 2023 s.109
* 'section 323 IPC' -> expected IPC 1860 s.323
* 'section 115 BNS' -> expected BNS 2023 s.115
* 'section 325 IPC' -> expected IPC 1860 s.325
* 'section 117 BNS' -> expected BNS 2023 s.117
* 'section 341 IPC' -> expected IPC 1860 s.341
* 'section 126 BNS' -> expected BNS 2023 s.126
* 'section 471 IPC' -> expected IPC 1860 s.471
* 'section 340 BNS' -> expected BNS 2023 s.340
* 'section 392 IPC' -> expected IPC 1860 s.392
* 'section 309 BNS' -> expected BNS 2023 s.309
* 'section 406 IPC' -> expected IPC 1860 s.406
* 'section 316 BNS' -> expected BNS 2023 s.316
* 'section 420 IPC' -> expected IPC 1860 s.420
* 'section 318 BNS' -> expected BNS 2023 s.318
* 'section 411 IPC' -> expected IPC 1860 s.411
* 'section 317 BNS' -> expected BNS 2023 s.317
* 'section 426 IPC' -> expected IPC 1860 s.426
* 'section 324 BNS' -> expected BNS 2023 s.324
* 'section 448 IPC' -> expected IPC 1860 s.448
* 'section 331 BNS' -> expected BNS 2023 s.331
* 'section 506 IPC' -> expected IPC 1860 s.506
* 'section 351 BNS' -> expected BNS 2023 s.351
* 'section 498A IPC' -> expected IPC 1860 s.498A
* 'section 85 BNS' -> expected BNS 2023 s.85
* 'section 363 IPC' -> expected IPC 1860 s.363
* 'section 137 BNS' -> expected BNS 2023 s.137
* 'section 147 IPC' -> expected IPC 1860 s.147
* 'section 191 BNS' -> expected BNS 2023 s.191

## Misses at k=10 — [CITATION] Hybrid (RRF)
* 'section 379 IPC' -> expected IPC 1860 s.379
* 'section 303 BNS' -> expected BNS 2023 s.303
* 'section 103 BNS' -> expected BNS 2023 s.103
* 'section 304 IPC' -> expected IPC 1860 s.304
* 'section 105 BNS' -> expected BNS 2023 s.105
* 'section 106 BNS' -> expected BNS 2023 s.106
* 'section 307 IPC' -> expected IPC 1860 s.307
* 'section 109 BNS' -> expected BNS 2023 s.109
* 'section 323 IPC' -> expected IPC 1860 s.323
* 'section 115 BNS' -> expected BNS 2023 s.115
* 'section 117 BNS' -> expected BNS 2023 s.117
* 'section 341 IPC' -> expected IPC 1860 s.341
* 'section 126 BNS' -> expected BNS 2023 s.126
* 'section 340 BNS' -> expected BNS 2023 s.340
* 'section 309 BNS' -> expected BNS 2023 s.309
* 'section 406 IPC' -> expected IPC 1860 s.406
* 'section 316 BNS' -> expected BNS 2023 s.316
* 'section 420 IPC' -> expected IPC 1860 s.420
* 'section 318 BNS' -> expected BNS 2023 s.318
* 'section 411 IPC' -> expected IPC 1860 s.411
* 'section 317 BNS' -> expected BNS 2023 s.317
* 'section 426 IPC' -> expected IPC 1860 s.426
* 'section 324 BNS' -> expected BNS 2023 s.324
* 'section 448 IPC' -> expected IPC 1860 s.448
* 'section 331 BNS' -> expected BNS 2023 s.331
* 'section 506 IPC' -> expected IPC 1860 s.506
* 'section 351 BNS' -> expected BNS 2023 s.351
* 'section 85 BNS' -> expected BNS 2023 s.85
* 'section 363 IPC' -> expected IPC 1860 s.363
* 'section 137 BNS' -> expected BNS 2023 s.137
* 'section 147 IPC' -> expected IPC 1860 s.147
* 'section 191 BNS' -> expected BNS 2023 s.191

## Misses at k=10 — [CITATION] Hybrid + cross-encoder
* 'section 303 BNS' -> expected BNS 2023 s.303
* 'section 302 IPC' -> expected IPC 1860 s.302
* 'section 105 BNS' -> expected BNS 2023 s.105
* 'section 109 BNS' -> expected BNS 2023 s.109
* 'section 117 BNS' -> expected BNS 2023 s.117
* 'section 340 BNS' -> expected BNS 2023 s.340
* 'section 309 BNS' -> expected BNS 2023 s.309
* 'section 316 BNS' -> expected BNS 2023 s.316
* 'section 324 BNS' -> expected BNS 2023 s.324
* 'section 331 BNS' -> expected BNS 2023 s.331
* 'section 85 BNS' -> expected BNS 2023 s.85
* 'section 147 IPC' -> expected IPC 1860 s.147

## Misses at k=10 — [CITATION] Routed (deterministic)
* 'section 303 BNS' -> expected BNS 2023 s.303
* 'section 117 BNS' -> expected BNS 2023 s.117
* 'section 309 BNS' -> expected BNS 2023 s.309
* 'section 316 BNS' -> expected BNS 2023 s.316
* 'section 324 BNS' -> expected BNS 2023 s.324
* 'section 331 BNS' -> expected BNS 2023 s.331


## Findings (belong in the paper, not only here)

1. **The cross-encoder destroys a quarter of the correct results hybrid retrieval already
   found** on natural-language queries: R@10 0.921 -> 0.684 (-25.7%). Mechanism: it demotes
   punishment sections below definitional cousins (the definition section of the same
   offence outranks the section carrying the penalty). This independently reproduces the
   IBPS finding that naive retrieval augmentation degrades a baseline. Original empirical
   result of this project.
2. **Dense retrieval scores 0.000 on citation-style queries** — embeddings cannot
   distinguish "section 479" from "section 480": adjacent-section confusion, exactly the
   failure the Extended Abstract names, now measured. Worse, through rank fusion the dense
   zero POISONS the hybrid (citation R@10: BM25 alone 0.842, hybrid 0.158).
3. **Mitigation is deterministic, not a model:** a regex router sends citation-shaped
   queries to the lexical leg alone. The routed configuration holds the best figures of
   each class simultaneously.
4. BM25's citation R@1 (0.132) exposes a second, distinct confusion: CROSS-ACT collision —
   "section 303" exists in IPC, BNS, BNSS and the Companies Act; disambiguation needs the
   act token weighted, which BM25 only partially achieves. Recorded unmitigated on
   2026-08-19; **MITIGATED 2026-08-26 (D-086)**: census over the corpus shows 510 of 723
   distinct section numbers exist in more than one act — the collision is the norm. The
   router, when built with the corpus directory, answers an act-less citation query whose
   number collides with one chunk per act (lookups, scored 0.0, never ranked) plus a
   `CrossActAmbiguity` note naming every act and choosing none. Act-named queries and the
   measured figures above are unchanged — the evaluation's citation queries all carry act
   tokens, so the numbers in this report stand as reported.
