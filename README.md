[![CI](https://github.com/vabhishekprakash/Bail_Reckoner/actions/workflows/ci.yml/badge.svg)](https://github.com/vabhishekprakash/Bail_Reckoner/actions/workflows/ci.yml)

# Bail Reckoner

![A terminal walk through the six gates of Section 479, recorded while the verified row count was still zero](05_docs/assets/hook.gif)

India's law entitles an undertrial prisoner to release once they have spent half the
maximum possible sentence in jail awaiting trial, or a third of it for a first offence.
That is Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023, and it is
arithmetic. The arithmetic mostly goes undone, which is why the Ministry of Law and
Justice posed it as a problem worth solving.

This system does the arithmetic. It walks six statutory gates in a fixed order, shows
every step, and cites the exact provision behind each one. It does not predict what a
court will do, it scores no one, and it decides nothing. The output is a working report a
legal-aid worker or jail officer can check line by line, plus a draft of the
application the jail Superintendent is legally required to make.

## The honest status, first

The engine is proved correct by 469 automated tests against synthetic fixtures. The
database of real offence punishments holds 5 verified rows out of 86, so the system
computes a real entitlement for those five offences and abstains on everything else. A
verified row requires a human to read the actual page of the actual statute and sign
their name. A machine drafted all 86 rows in the review queue; the same machine signing
them would be the machine agreeing with itself. The other 81 are unsigned drafts, and
no draft row is visible to the engine, so a demonstration on one of those offences runs
on synthetic fixtures, labelled as such.

This is the project's central design position. Where the law is unsettled, the system
flags and routes to a human. Where a value could not be detected, it says so instead
of substituting something plausible. The same defect (a plausible answer where a
refusal belongs) was found and eliminated six separate times during construction, each
time converted into a rule with a test.

The git history here starts at a handful of commits because the original repository was
lost and the finished project was re-uploaded. The commit count is not the development
record.

## A real computation

Theft under IPC section 379, one of the five signed rows. The maximum comes from the
printed page a person read and signed; the custody dates are illustrative. Abridged
here: the full report also carries the multiple-case assessment and the standing
caveats about State amendments and special statutes.

```text
 SECTION 479 BNSS 2023 — ENTITLEMENT COMPUTATION REPORT

STATUS
  Statutory entitlement to release under Section 479(1), BNSS 2023 is
  established on the inputs provided.

CUSTODY
  Date of arrest:       10 January 2025
  Computed as on:       18 September 2026
  Custody undergone:    617 days
  Effective custody:    617 days

CASE Illustrative example, not a real case  (pending)
  Offence: Theft
    Section:            379
    Maximum sentence:   3 years
    Fraction applied:   one-third
    Threshold:          12 months
    Status: threshold reached on 10 January 2026

Legally reviewed by: ______________________    Date: ____________
  Statute version:      BNSS 2023@2025-10-06+dt-0.2.0+20976f7d
  Law in force on:      2026-09-18
  Inputs hash:          b3a7cee0f0bb40ea2633a1a00f54c34369a98bf2f1dc2022dff0294c826ae430
```

The review line stays blank because no advocate has reviewed this project. An offence
whose row is still unsigned returns `OFFENCE_NOT_IN_DATABASE` instead of a number.

## What is inside

A pure decision engine with no model, no network and no file access in the decision
path, so its correctness is provable rather than measured. Around it: search over
2,245 sections of 8 acts, verbatim extracts from Supreme Court judgments (never
summaries, because a summary could hallucinate a citation), a text-extraction seam
with a mandatory human confirmation step, a REST API whose every response states how
many verified rows exist, a server-rendered interface under hard design rules (no
colour ever encodes an outcome), a deterministic PDF generator for the court filing,
and an append-only audit log with a hash chain.

Every source document carries a SHA-256 hash re-verified by the test suite. Every
measured number states its claim class, and classes are never blended: the only
claimable accuracy is the independently recomputed arithmetic. Two of the retrieval
findings are original results: a cross-encoder reranker destroyed a quarter of correct
results, and dense embeddings scored 0.000 on citation-style queries.

## Running it

On Windows, run `python` instead of `python3`, and use `.venv\Scripts\` wherever the block
says `.venv/bin/`.

```bash
cd 06_src
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python -c "from bail_reckoner.retrieval.corpus import build_corpus; build_corpus()"
.venv/bin/python -c "from bail_reckoner.statutes.review_queue import build_database; print(build_database())"
.venv/bin/python -m pytest -q                 # 468 pass, 1 skip by design, about 10 minutes
.venv/bin/uvicorn --factory bail_reckoner.api.app:create_app
```

You need Python 3.12. The lock file pins numpy 2.5.2, which needs 3.12 or newer, and
rapidocr-onnxruntime 1.4.4, which does not install on 3.13.

The corpus build takes about 30 seconds, and you run it once per clone. Without the
corpus, the 18 retrieval tests (Layer A) skip rather than fail, and a fresh clone reports
450 passed and 19 skipped.

The second build loads the signed rows from the review queue into the penalty store and
prints the row counts, `{'DRAFT': 0, 'VERIFIED': 5}` today. Run it again after signing a
row; without it the API serves an empty store and every offence abstains. Start with
[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

## How AI was used

I built this with an AI coding agent (Anthropic's Claude) working under my direction.
It wrote code, drafted documents, and ran verification. Every consequential decision
came to me for approval, every statutory text was checked against the official gazette
or India Code, and the review of actual law pages is human work that no machine output
replaces: the database carried zero verified rows until a person read the pages and
signed the first five. The AI is not an author here. I built this project, and a complete engineering
log of the AI-assisted sessions, including every decision and the reasoning behind it,
is kept outside this repository and is available on request. Documents here
sometimes cite that log's entry numbers (D-numbers) or its files by name
(DECISIONS.md, RULES.md, PROGRESS.md, OPEN_ITEMS.yaml); those live with the
private record, not in this repository, as do the Extended Abstract and the
presentation deck that several documents cite for the project's original scope.


No legal professional reviewed this project. It is a
decision-support aid. It is never a decision-maker.
