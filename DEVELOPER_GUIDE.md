# Bail Reckoner: Developer Guide

*Written 2026-09-02 for any developer or evaluator meeting this project for the first
time. Plain language on purpose; project jargon is explained the first time it appears.
The guide follows the project's own honesty rules while describing them: no figure
appears without saying what it can and cannot claim.*

**Legally reviewed by: ______________ (empty until a qualified human signs. No advocate
or law-faculty reviewer has ever been available to this project, so every legal-judgement
label in it is indicative, never verified.)**

---

## 0. The one fact that governs everything else

**The system currently computes nothing about any real offence.** It is fully built and
heavily tested, but its database of offence punishments contains **zero verified rows**,
because verifying a row means a human reading the actual page of the actual statute and
signing their name, and that act is deliberately reserved for the project lead. A machine
drafted those rows; if the same machine "verified" them, the verification would be the
machine agreeing with itself, and every number downstream would be circular. Until the
86-row review queue is signed, every demonstration runs on synthetic fixtures, made up
and clearly labelled as such. This is a design position, not an accident, and it is the
first thing to understand about the codebase.

## 1. What this project is

An AI-powered "Bail Reckoner" (problem statement SIH1702, set by the Ministry of Law
and Justice) that computes an undertrial prisoner's statutory entitlement to release
under Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023, India's successor
to the old Code of Criminal Procedure. The law says, roughly: a person held in jail
awaiting trial must be released once they have served half the maximum sentence the
charged offence could carry, or a third of it for a first offence. That is arithmetic.
This system does the arithmetic, shows every step, and cites the exact legal provision
behind each step.

What it is not, and this is load-bearing: it does not predict whether a court will
grant bail, does not score "flight risk" or any other discretionary factor, and has no
power to decide anything. It is a calculator with citations for legal-aid workers,
review committees and jail officers. It even refuses to have an "ineligible" output.
Its only two verdicts are *entitlement established* and *no entitlement identified,
human review required*, because a wrong "eligible" gets caught by a court, while a
wrong "ineligible" silently keeps a person in jail.

## 2. What was built: four layers, in four different states of "done"

The honest status of each layer (never say "all layers built" without this table):

| Layer | What it does | Honest state |
|---|---|---|
| **C, the engine** | Six ordered legal "gates" plus custody arithmetic, producing the verdict, the report and the court filing | **Built and proved.** Every gate and proviso has tests, outputs are byte-compared against golden files, and the arithmetic is independently recomputed. The one layer whose correctness is proved rather than measured. |
| **A, retrieval** | Search over 2,245 sections of 8 acts, to find the law | **Built and measured.** Recall figures by query class in `04_eval/`. |
| **D, precedent** | Verbatim extracts from Supreme Court judgments; never summaries, because a summary could hallucinate | **Built but unscored**, over a corpus permanently labelled INCOMPLETE: 3 of 4 judgments, and the fourth is behind a captcha and stays unacquired rather than substituting an unofficial copy. |
| **B, extraction** | Reads case text into candidate offences for a human to confirm | **A seam with no model.** A deterministic pattern-matcher plus a mandatory human confirmation step. No trainable model is feasible in this environment, and the record says so plainly. |

Around them sits a REST API (FastAPI) whose every response carries an honesty envelope
("verified rows: 0", with a warning, until that changes) and which returns engine
refusals as clear 422 responses carrying the reason instead of blank server errors.
There is a server-rendered web interface under hard design constraints: no colour or
icon ever encodes an outcome, nothing hides behind a toggle, and affirmations are never
pre-ticked. A deterministic PDF generator produces the s.479(3) application in pure
standard library, so the same inputs give byte-identical files. An append-only audit
log carries a hash chain, with its head state kept outside the log so truncation is
detectable.

## 3. How it was built: the rules that shaped everything

1. **The engine is pure.** Layer C has no network, no model, and no file access in the
   decision path: deterministic functions over typed inputs. An import-level test fails
   if the engine ever imports retrieval, extraction, precedent, or a model library.
   This purity is what makes correctness provable.
2. **Statutory text is verified against the official gazette before encoding.** That
   rule paid for itself on day one. The gazette contains an Explanation to s.479(1),
   excluding delay caused by the accused from the custody count, that was missing from
   every secondary source the project had.
3. **No value on a statutory path gets a convenience default** (rule D-064). A zero, a
   None, an absent result there is a failed detection to report, never a value to
   substitute. The project's recurring bug, found and fixed six separate times, is what
   it calls "a plausible answer where a refusal belongs": a `max(1, ...)` that turned a
   failed count into "one"; a fabricated cross-code mapping; silently dropped sections;
   a hidden unresolvable candidate; a search that answered an ambiguous query with one
   act's section when 70% of section numbers exist in several acts; a custody clamp
   that turned contradictory inputs into a plausible zero. Each instance became a rule
   with a test. If you extend this codebase, this is the bug you will write next, so
   look for it.
4. **Every consequential choice is a recorded decision.** The project keeps a
   decision log of about 90 entries (the D-numbers cited throughout the code and
   docs), each with options, trade-offs, the cost accepted, and approval status.
   Disputed calls also went through a structured multi-perspective review before
   they stood. The log lives with the private engineering record and is available
   on request.
5. **Every source document carries provenance.** `01_law/SOURCES.md` records 13
   accepted documents (10 statutes, 3 Supreme Court judgments) with SHA-256 hashes that
   a recurring test re-verifies, and a rejected list of five official-looking files
   that turned out incomplete, stale, or mislabelled. The lesson from those five: a
   filename is not provenance. Open the file before believing its label.
6. **Every number carries its claim class**, and classes never blend:
   * Tier 1: arithmetic, independently recomputed. The only claimable accuracy.
   * Tier 2: legal-judgement labels by a non-advocate. Indicative only, forever.
   * Retrieval measurement: search recall, with no legal judgement involved.
   * Qualified floor: Layer B's perfect score on synthetic text, which measures a
     pattern-matcher on 38 known sections, not real charge-sheet extraction.
   * Self-scored: the builder scoring its own retrieval. Never an evaluation figure.
   * Cross-channel agreement: two machine channels (the PDF text layer, and OCR of the
     rendered page) agreeing on 26 of 39 readable sections. Not verification, since two
     machines can be wrong together, but the 13 disagreements tell the human reviewer
     which pages to read first.

## 4. Where things live

```
H:\Bail_Reckoner\
├── DEVELOPER_GUIDE.md   this file
├── 00_inputs\           original brief (read-only)
├── 01_law\              gazette texts, bare acts, judgments, and SOURCES.md (hashes)
├── 02_data\             decision table (YAML), report language (YAML), review queue
├── 03_goldenset\        labelled test cases, two-tier
├── 04_eval\             every measurement, each stating its claim class
├── 05_docs\             ledger, reports, paper, UI spec
└── 06_src\              all code: bail_reckoner\{engine, statutes, retrieval,
                         extraction, precedent, reporting, audit, api}, tests\
```

Section 5 walks a first-time setup step by step. The short version: Python 3.12, venv
in `06_src/.venv`, install from `requirements.lock`, rebuild the retrieval corpus once,
then `pytest`. The full suite runs green from a cold clone; we know because a cold
clone once caught a real line-endings bug the working checkout could never see.

## 5. A beginner's guidebook: running this project

You need a Windows or Linux machine, Python 3.12, and about twenty minutes. Nothing
here touches the internet at runtime, so an offline machine works fine once the
packages are installed.

**Step 1. Get the code.** Clone the repository, or copy the whole folder. Everything
lives under one directory; there is no database server to install and no account to
create.

**Step 2. Make a Python environment.** Open a terminal in the `06_src` folder and run:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.lock        (Windows)
.venv/bin/pip install -r requirements.lock            (Linux/Mac)
```

The lock file pins every package to an exact version. Installation takes a few
minutes because the search components pull in PyTorch.

**Step 3. Build the search index.** One derived file is not stored in git and has to
be built once from the law texts that are:

```
.venv\Scripts\python -c "from bail_reckoner.retrieval.corpus import build_corpus; build_corpus()"
```

You should see it report 2,245 sections. If it reports anything else, stop and check
that the PDFs in `01_law` are intact; the test suite verifies their hashes.

**Step 4. Run the tests.** This is the fastest way to know your setup is healthy:

```
.venv\Scripts\python -m pytest -q
```

Expect every test green, with exactly one skip that announces itself and explains why. The
run takes about ten minutes; most of that is one test that reads a large PDF.

**Step 5. Start the server and open the page.**

```
.venv\Scripts\uvicorn --factory bail_reckoner.api.app:create_app
```

Then open `http://127.0.0.1:8000` in a browser. Fill in an arrest date, a section
number such as 901, and tick the affirmations. Pick "synthetic" as the source of
maxima, since no verified rows exist yet. Press compute. The page shows the full
report, character for character the same document the tests pin, and can produce the
draft court application as a PDF.

**When something refuses, that is the system working.** Give it a computation date
earlier than the arrest date and you get a clear message saying the inputs contradict
each other. Ask for a real section and it tells you no verified row exists. Ask for
the court filing on a contested case and it declines, with reasons. None of these are
bugs. Refusing loudly instead of guessing quietly is the design, and if you extend
the code, the tests will hold you to it.

**Where to go next.** Read a gate in `06_src/bail_reckoner/engine/gates.py` next to
its test; each one cites the sub-section of law it implements. Then skim
the decision log for whatever part you want to change. Someone probably already
recorded why it is the way it is.

## 6. What remains, and whose it is

As of this writing:

The owner's, and the only thing that unblocks real computation: **verify the 86-row
penalty queue** (59 review-first; the sanity-pass rows lead). The cross-channel
reconciliation in `04_eval/` cuts the reading down, with 13 disagreement pages to read
first. A human signature on those rows is the single act that makes the system compute
something real. Everything else once on this list was resolved or ratified on
2026-09-04, with each closure recorded.

Nobody's, permanently, stated without softening: a Layer B model (infeasible here);
the fourth judgment (captcha-gated, and no unofficial substitute, ever); advocate
review (unavailable, so Tier 2 stays indicative forever); and Hindi or Telugu
interface text, which waits for a human translator because machine translation of
legal-adjacent language was firmly rejected on review.

## 7. What this project is not

Not operational. Not advocate-reviewed. Never tested on a real charge sheet, by
design: no real accused person's data exists anywhere in it. Carrying no model in
Layer B. And not finished in the everyday sense. It is complete only in the sense the
project defines: every machine-completable surface built, tested and truthful, and
every human act named, queued, and waiting for its human.
