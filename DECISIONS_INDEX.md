# Decision index

The code cites decisions by number, as in "per D-064". The decision log itself, with the
options weighed, the cost accepted and the approval status of each entry, is part of the
private engineering record described in the README. This index gives the number, the date
and the title of every decision the package code cites, so a citation can at least be read.
Entries the code does not cite are left out. Titles are the log's own, shortened where a
status suffix or an internal reference added nothing.

| Decision | Date | Title |
|---|---|---|
| D-009 | by 2026-08-12 | Discretionary factors are never scored |
| D-010 | by 2026-08-12 | The system has no "ineligible" output state |
| D-012 | by 2026-08-12 | No bail-outcome prediction, and this is stated explicitly |
| D-025 | 2026-08-12 | s.479(2) scope is configurable; default NARROW, single-FIR multi-section flagged CONTESTED |
| D-026 | 2026-08-12 | MVP input is structured form fields; text input widens later |
| D-027 | 2026-08-12 | SQLite, with the schema written for mechanical PostgreSQL migration |
| D-028 | 2026-08-12 | Custody computed from the date of arrest, first-remand date also captured (unverified) |
| D-030 | 2026-08-12 | Multilingual is interface-only (English, Hindi, Telugu); input parsing stays English |
| D-033 | 2026-08-12 | Gate 3 reclassified from BAR to FLAG (SPECIAL_STATUTE_TEST_REQUIRED) |
| D-034 | 2026-08-12 | Third-proviso absolute cap promoted to gate 0 (DETAINED_BEYOND_MAXIMUM) |
| D-035 | 2026-08-12 | Barred reports show the working; the pitch-deck slide is not the report template |
| D-036 | 2026-08-12 | M1 offence seed list policy: 40 to 60 entries, six mandatory coverage criteria |
| D-038 | 2026-08-12 | Judgment-derived data: redacted only, quarantined in 02_data, never committed |
| D-039 | 2026-08-12 | Multiple charges: the highest maximum governs the person-level entitlement (unverified) |
| D-040 | 2026-08-12 | Second proviso: a standing report note, never a gate |
| D-042 | 2026-08-12 | POCSO: no barring provision invented; the field stays null |
| D-045 | 2026-08-12 | The s.479 text in the operating rules updated to gazette-verified status; the Explanation added |
| D-046 | 2026-08-12 | M1 offence seed list: drafted composition, every row verified by a person before entry |
| D-047 | 2026-08-12 | Custody arithmetic conventions, including the s.479(1) Explanation |
| D-048 | 2026-08-12 | Output-object taxonomy: a binary verdict plus typed flags |
| D-049 | 2026-08-12 | The statute_version definition |
| D-050 | 2026-08-12 | Engine dependency policy: Layer C is stdlib-only |
| D-051 | 2026-08-12 | "First-time offender" input semantics |
| D-052 | 2026-08-12 | s.479(2) input shape |
| D-054 | 2026-08-12 | Gate 3 statute set is the Antil Category C list only |
| D-055 | 2026-08-12 | Supersedes D-053: statutory parameters are versioned data; gate composition is typed Python |
| D-058 | 2026-08-12 | Frontend design requires the owner's approval; he supplies the style direction |
| D-060 | 2026-08-12 | A user-supplied maximum may never reach gate 0 or gate 5 |
| D-061 | 2026-08-12 | Penalty rows re-keyed on (regime, section, sub-section, variant): one row per punishment limb |
| D-064 | 2026-08-12 | Standing rule: no convenience default on any path feeding a statutory value |
| D-065 | 2026-08-13 | M3 golden-set and harness design |
| D-066 | 2026-08-13 | Gate 0 computes against both cap bounds; the band is flagged, not decided |
| D-067 | 2026-08-13 | D-046 criterion (iv): NDPS quantity-band rows; PMLA deferred |
| D-068 | 2026-08-19 | Report design: language, object/renderer split, styling rules |
| D-069 | 2026-08-19 | Penalty-store staleness key stays content-only; the schema version is excluded |
| D-070 | 2026-08-19 | Section-versus-contents discrimination is structural, not vocabulary |
| D-071 | 2026-08-19 | s.479(3) application generator: refusal conditions, provenance split, blanks left blank |
| D-072 | 2026-08-19 | Gates 0, 1 and 5 compute over pending offences only |
| D-073 | 2026-08-19 | PDF renderer: a stdlib-only minimal writer, no new dependency |
| D-074 | 2026-08-19 | Gate 3 fires on an offence in scope, not on statute membership |
| D-075 | 2026-08-19 | The OLQ-2 person-level rule gets the D-066 band, widened to dual dates |
| D-076 | 2026-08-19 | REST API before any UI: the contract over Report and Application |
| D-077 | 2026-08-19 | Frontend: hard UI constraints, a stack-neutral demonstrator, two conflicts surfaced |
| D-078 | 2026-08-19 | A technology named in a milestone plan is intent, not approval: every dependency needs its own recorded ratification |
| D-080 | 2026-08-19 | rank_bm25 0.2.2 for Layer A's lexical leg |
| D-081 | 2026-08-19 | sentence-transformers 6.0.0 (MiniLM bi-encoder, ms-marco cross-encoder) |
| D-082 | 2026-08-19 | FAISS declined: exact numpy search instead |
| D-084 | 2026-08-26 | Frontend stack: server-rendered first (the D-058 formal call) |
| D-085 | 2026-08-26 | pypdfium2 with pillow as the dev-only rasteriser for the D-073 layout gate |
| D-086 | 2026-08-26 | Cross-act section-number collision: surface every act, never rank one silently |
| D-087 | 2026-08-26 | Multilingual scope: English-only documents, multilingual interface chrome |
| D-089 | 2026-08-29 | Second extraction channel by OCR: RapidOCR over PDFium rasters, dev-only |
| D-090 | 2026-09-02 | What "complete the entire project" means, and the completion scope |
| D-091 | 2026-09-02 | Precedent corpus reads the Supreme Court's own Antil print; the mirror copy superseded |
| D-092 | 2026-09-02 | API refusal-translation layer: engine refusals become 422s that carry their reason |
