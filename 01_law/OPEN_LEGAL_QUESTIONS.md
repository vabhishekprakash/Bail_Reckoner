# OPEN LEGAL QUESTIONS — Bail Reckoner

**Purpose.** Every legal question this project cannot resolve itself, in one page, so that one
hour of a practising advocate's time can clear the entire backlog at once. Each entry states the
question, why it matters, **the conservative default currently coded**, and what would change if
answered. **Append, never rewrite.** Every legal uncertainty goes here the moment it is found.

Created 2026-08-12 (session 2). Cross-references: `DECISIONS.md`, `CONTEXT.md` §7,
`05_docs\Step1_interrogation_report.md`.

**STATUS CHANGE 2026-08-19 — see the notice at the end of this file: no advocate review is
available to this project, permanently. Every "If answered" clause below is counterfactual.**

---

## OLQ-1 — Does a Category-C special-statute bar extinguish, or merely qualify, the s.479 entitlement? And does the NDPS s.37 position follow *Badshah* on PMLA?

**Question.** *Badshah Majid Malik v. ED* (SC, Crl. A. No. 4258/2024, 27 Dec 2024) holds
s.479(1) BNSS applies to PMLA prosecutions notwithstanding PMLA s.45. Does the same logic govern
NDPS s.37, UAPA s.43-D(5), Companies Act s.212(6), and POCSO — i.e. is s.479 a freestanding
entitlement that overrides every special-statute twin-condition test, or does each special
statute's bar qualify or exclude it?
**Why it matters.** Determines whether gate 3 could ever lawfully be terminal for any statute,
and what the report must say to a jail Superintendent about a special-statute undertrial.
**Conservative default coded.** Gate 3 is a FLAG, never a terminal bar (D-033):
`SPECIAL_STATUTE_TEST_REQUIRED`, arithmetic displayed in full, applicable provision quoted
verbatim, human review required. The NDPS position is treated as **unsettled** — not assumed to
follow *Badshah*.
**If answered.** Per-statute behaviour becomes citable: statutes confirmed to follow *Badshah*
get the holding cited in the report; any statute authoritatively held to exclude s.479 gets a
distinct, cited routing.

**Lead added 2026-08-12 (session 11) — *Union of India v. K.A. Najeeb*, SC, 1 February 2021,
reported as (2021) 3 SCC 713.** Reported to hold that an undertrial prosecuted under UAPA **may
be granted bail on prolonged incarceration**, notwithstanding s.43-D(5), because the right to a
speedy trial under Article 21 is a fundamental right; bail was granted after roughly five years'
custody with 200-plus witnesses still to examine.

If that report is accurate it bears directly on this question, because it is the **same
architectural move as *Badshah***: a Category-C statutory bar yielding to an independent route to
release. It would support the design already coded — gate 3 as a FLAG that never extinguishes the
computation (D-033).

**Two cautions, both material.** First, Najeeb is **constitutional** (Article 21, delay), not
statutory, so it does *not* by itself decide whether **s.479 BNSS** overrides s.43-D(5) — a
different question with a different mechanism. Second, **this project has read only secondary
summaries of it, not the judgment** (source: search results, `indiankanoon.org/doc/18346623/`).
Under C5 that makes it a lead to check, not an authority to rely on. **Do not cite it in any
generated report until the judgment is in `01_law\`.**

## OLQ-2 — When several offences are charged, which maximum sentence governs the person-level threshold?

**Question.** s.479(1) speaks of "that offence". With multiple charged offences, does the
threshold run per-offence, on the gravest charge, or otherwise?
**Why it matters.** Directly changes the qualifying date — the system's central output.
**Conservative default coded.** Per-offence arithmetic displayed for all; the person-level
entitlement uses the **highest** maximum among charged offences — the longest threshold, the
reading that never overstates an entitlement (D-039, `[UNVERIFIED]`).
**If answered.** The aggregation function and the report's person-level threshold line change;
per-offence rows are unaffected.

## OLQ-3 — Does the s.479(2) bar ("shall not be released on bail") reach the first-proviso bond route?

**Question.** s.479(2) bars release "on bail"; the first proviso releases a first-time offender
"on bond". Is a first-time offender with multiple cases pending barred from the bond route?
**Why it matters.** First-time offenders are the ⅓-threshold class the project most wants to
surface; the answer decides whether multi-case first-timers are barred or entitled.
**Conservative default coded.** The bar reaches both routes; affected cases flagged `CONTESTED`
and routed to human review (D-041, `[UNVERIFIED]`).
**If answered.** Either the flag is removed (bar reaches both — confirmed) or multi-case
first-timers proceed to gate 5 on the ⅓ threshold with the holding cited.

## OLQ-4 — Which POCSO provision, if any, constitutes the Category-C stringent bail bar?

**NARROWED 2026-08-12 on reading the bare act — the original question is answered.**
The Act has now been read (`POCSO_2012_Act32_IndiaCode_asOn_2023-02-28.pdf`, post-2019 text) and
**there is no twin-condition bail bar in it.** The word "bail" occurs **exactly once** in the
whole Act, in **s.31**, which *applies* the CrPC "including the provisions as to bail and bonds"
to Special Court proceedings — the opposite of restricting them. None of the NDPS s.37 markers
("shall not be released on bail", "reasonable grounds for believing", "not guilty of such
offence") appear anywhere in the Act.

**The remaining question is a different one: on what basis does *Satender Kumar Antil* place
POCSO in Category C, and what should gate 3 say about it?** Four candidate explanations, none of
which this project can confirm — all Tier-2:

**(a) The statutory presumptions.** POCSO **s.29** (presumption of guilt) and **s.30**
(presumption of culpable mental state) bear heavily on bail in practice without being bail bars.
*If so:* the report should name ss.29–30 as the basis instead of reporting a missing provision.

**(b) Co-charging carries the severity, not POCSO itself.** POCSO offences are commonly charged
alongside IPC/BNS offences punishable with life imprisonment, so in the cases that matter **gate 1
has already fired** on the co-charged offence and gate 3 adds nothing. *If so:* POCSO's presence
in the gate-3 set is close to inert in practice, and the honest report line says the severity came
from the co-charged offence.

**(c) Category C describes practice, not statutory text.** *Antil* may be grouping Acts by how
bail is *approached* in them rather than asserting that each contains a twin-condition bar. On
that reading the absence of a bar in POCSO is not an anomaly at all and the category was never a
claim about text. *If so:* the whole `provision` field is the wrong shape for POCSO, and the row
should carry a practice note rather than a null provision.

**(d) The listing is imprecise.** Secondary sources summarising *Antil* may have grouped POCSO
loosely. This project has read neither the judgment nor a reliable report of it
(`CONTEXT.md` §7 item 29), so it cannot exclude this. *If so:* POCSO leaves the gate-3 set.

**Reading *Antil* itself would discriminate between (a)–(d)** and is the single highest-value
acquisition still outstanding for gate 3.
**Why it matters.** Gate 3 currently flags POCSO with an unresolvable provision, which reads
oddly in a report. If Category-C membership rests on the presumptions rather than on a bar, the
report should say *that*, naming ss.29–30, instead of reporting a missing provision.
**Conservative default coded.** Unchanged: gate 3 surfaces POCSO's Category-C membership with the
provision field **null** (D-042), and the report states the provision is unresolved — now on
evidence rather than for want of looking.
**If answered.** Either the report names ss.29–30 as the basis, or POCSO leaves the gate-3 set
with the *Antil* listing annotated. Both are one-line data edits under D-055.

## OLQ-5 — Does a single FIR charging multiple sections trigger s.479(2)?

**Question.** s.479(2) fires on "more than one offence or in multiple cases". Does one FIR with
several charged sections count as "more than one offence" (broad), or does the bar require
multiple cases (narrow)? Genuinely unsettled; multi-section FIRs are the norm.
**Why it matters.** Decides the bar's reach over a large share of real undertrials — the
"exception swallowing the rule" criticism.
**Conservative default coded.** Default NARROW: the bar fires on multiple *cases*; a single FIR
with multiple sections is flagged `CONTESTED` and routed to human review, never silently cleared
in either direction. Both readings implemented and switchable (D-025).
**If answered.** The default configuration is set to the authoritative reading and the flag
narrows accordingly, with the holding cited.

## OLQ-6 — Does the s.479 threshold run from the date of arrest or the date of first remand?

**Question.** From which date does "detention … undergone" accrue?
**Why it matters.** Days matter: every week of threshold error is a week of custody the law did
or did not require.
**Conservative default coded.** Custody computed from **date of arrest**; date of first remand
also captured; both shown; divergence flagged (D-028, `[UNVERIFIED]`).
**If answered.** The primary custody clock is set to the authoritative rule; both dates remain
displayed.

## OLQ-9 — Is the day of arrest counted as a day of detention undergone? *(added 2026-08-12, session 8, on building the engine)*

**Question.** s.479(1) speaks of detention "undergone" for a period. If a person is arrested on
1 January, has one day been undergone on 1 January, or none? Inclusive versus exclusive counting.
**Why it matters.** One day, on every single computation. At the margin it decides whether
someone qualifies today or tomorrow.
**Conservative default coded.** **Inclusive** — the day of arrest counts. This yields the earlier
qualifying date, which is the direction D-010 requires: a threshold reached slightly too early
produces a claim a court will test, while one reached slightly too late keeps a person in custody
with nobody to appeal to. Implemented in `engine/custody.py::compute_custody`.
**If answered.** One line in `compute_custody`; every stored report's arithmetic shifts by a day,
so the change must bump `statute_version`.

## OLQ-9a — Does the third-proviso cap apply to an offence excluded from s.479(1) by the death/life carve-out? *(added 2026-08-12, session 8)*

**Question.** The third proviso ("no such person shall in any case be detained … for more than
the maximum period") sits *inside* s.479(1), whose main clause excludes offences punishable with
death or life. Does the cap therefore not reach those offences at all — or does it apply
generally?
**Why it matters.** Decides whether gate 0 may fire for a person charged with a death/life
offence, i.e. whether the system reports someone held beyond a co-charged offence's maximum.
**Conservative default coded.** Gate 0 is computed and its flag raised **regardless** of gate 1.
Over-flagging costs a human review; under-flagging costs someone their liberty. The flag is
surfaced as an urgent condition for a human, never as a grant of entitlement.
**If answered.** Either gate 0 is suppressed where gate 1 fires, or the current behaviour is
confirmed and can be stated with authority rather than as a precaution.

## OLQ-10 — When a threshold falls part-way through a month, does the part-month round or floor? *(added 2026-08-12, session 8)*

**Question.** One-third of a ten-month maximum is 3⅓ months. The ⅓ has to become whole days.
Round to nearest, floor, or ceiling?
**Why it matters.** Up to a day or two on every non-divisible threshold, and one-third thresholds
are rarely divisible.
**Conservative default coded.** **Floor**, in `engine/custody.py::add_months_fraction`, for the
same asymmetry reason as OLQ-9. Month-end overflow also clamps down (31 January + 1 month =
28/29 February) for consistency.
**If answered.** One line; same `statute_version` consequence as OLQ-9.

## OLQ-8 — Which statutes actually belong in gate 3's special-statute set? *(added 2026-08-12, session 4, on reading the Extended Abstract and Context Window v1)*

**Question.** The project's own documents give **two different sets**. The *Satender Kumar Antil*
Category C list — used in CLAUDE.md §3, EA §2.4 and deck slide 11 — is NDPS s.37, PMLA s.45,
UAPA s.43-D(5), Companies Act s.212(6), POCSO. But the narrative text in EA §1 and Context Window
v1 §3 lists "NDPS, PMLA, UAPA, POCSO, **the SC/ST Act, the IT Act**" — dropping the Companies Act
and adding two statutes that appear in no Category C listing. Which set does gate 3 encode, and
does each named statute in fact carry a stringent bail bar of the NDPS s.37 twin-condition kind?
**Why it matters.** Gate 3 fires `SPECIAL_STATUTE_TEST_REQUIRED` and must name and quote the
applicable provision. A statute wrongly included routes cases to human review that need not be;
one wrongly omitted lets a case through without the test attached. Note the SC/ST Act's bail
provision (s.18, barring anticipatory bail) is a different animal from an NDPS-style bar on
regular bail — inclusion cannot be assumed from a prose list.
**Conservative default coded.** Gate 3's set is the **Antil Category C list only** (the list with
judicial provenance), with POCSO's provision field null per D-042. SC/ST Act and IT Act are
**not** encoded, and their absence is recorded here rather than silently assumed. Any statute
enters the set only with its barring provision read from the bare act (C5, D-042).
**If answered.** The set is fixed per statute with its provision quoted; each addition needs its
bare act in `01_law\` first.

## OLQ-7 — What counts as "delay in proceeding caused by the accused" under the s.479(1) Explanation, and who determines it? *(added 2026-08-12, session 2, on gazette verification)*

**Question.** The gazette text carries an Explanation absent from every pre-M0 project document:
*"In computing the period of detention under this section for granting bail, the period of
detention passed due to delay in proceeding caused by the accused shall be excluded."* What
qualifies as accused-caused delay (adjournments sought? absconding? frivolous applications?),
must it be judicially determined, and how is it evidenced on a jail record?
**Why it matters.** It directly reduces the custody figure used in gates 0 and 5 — the core
arithmetic. Ignoring it overstates custody served; guessing it is legal judgement the engine must
not perform.
**Conservative default coded (proposed at Step 2, D-047 — pending).** The engine takes an
optional `excluded_days` input defaulting to **zero**, used only when a court-determined
exclusion is supplied; the engine never computes or attributes delay itself; every report quotes
the Explanation verbatim and states the exclusion figure used (zero included). With
`excluded_days = 0` the computed custody is the *maximum* the person could claim — a threshold
not crossed at zero exclusions is not crossed under any exclusion, so the entitlement is never
overstated by the default. The reverse is flagged: a threshold *crossed* at zero exclusions may
be uncrossed once a real exclusion applies, so crossings carry an exclusion-status caveat until
verified.
**If answered.** The input's evidentiary requirements and the caveat's wording get grounded in
the authority; the default stays zero.

## OLQ-11 — Does the third-proviso cap measure against each charged offence's own maximum, or the governing (highest) maximum? *(added 2026-08-13, session 17 — caught by the first golden-set smoke run)*

**Question.** A person is charged with offence E (maximum 6 months) and offence A (maximum
36 months) and has been in custody 12 months. Custody exceeds E's own maximum but not A's. Does
the s.479(1) third proviso ("no such person shall in any case be detained … for more than the
maximum period of imprisonment provided for **the said offence**") fire per offence, or only
against the highest maximum among the charges — on the reasoning that detention is justified by
the gravest charge?
**How it surfaced.** Smoke case SMOKE-05 was hand-labelled expecting `DETAINED_BEYOND_MAXIMUM`
on the per-offence reading; the engine, which measures gate 0 against the governing maximum
(D-039), did not flag. The harness guard caught the disagreement on its first run.
**Why it matters — a conservatism inversion, previously unrecorded.** D-039's highest-maximum
rule is the *safe* direction for gate 5 (longest threshold — never overstates an entitlement)
but the *unsafe* direction for gate 0 (latest possible cap alert — the urgent flag fires as late
as it possibly could). One rule cannot be conservative for both gates at once. This is L-001's
"what does 'the offence' attach to" question, surfacing a third time, now inside a single
person's charge sheet.
**Conservative default coded — REVISED 2026-08-13 per D-066 (flag-not-pick, the D-025
pattern).** Gate 0 now computes against **both bounds**: custody at or past the governing
(highest) maximum → `DETAINED_BEYOND_MAXIMUM` as before; custody at or past the **lowest**
charged maximum but below the highest → `CONTESTED_CAP_BASIS`, routed to human review. Neither
reading is adopted. The change matters most where gate 2 bars: s.479(2) is expressly subject to
the third proviso, so the cap is the only surviving route to relief there, and the earlier
highest-only rule made that sole route fire as late as it possibly could. Golden cases whose
labels depend on this question carry `depends_on_olq: [OLQ-11]` and surface by query.
**If answered.** *Per offence* → the band collapses downward: the contested flag becomes
`DETAINED_BEYOND_MAXIMUM` at the lowest crossed maximum. *Governing maximum* → the band
collapses upward: the contested flag is dropped. Either way, one function change plus the
relabelling of every `depends_on_olq: [OLQ-11]` case, each with reasoning.


---

## STATUS CHANGE — 2026-08-19 (appended per the file's append-only rule)

**No advocate review is available to this project, permanently** (Abhishek, 2026-08-19). The
premise in this file's header — that one hour of a practising advocate's time can clear the
backlog — no longer holds and will not. Every question above moves from *awaiting resolution*
to **open and unresolvable within this project**. Each entry's "Conservative default coded" is
therefore the system's **permanent behaviour**, and each "If answered" clause is
counterfactual: it records what a resolution would have changed, not what any pending process
will change. The consolidated statement of all open questions, their permanent defaults, the
safe-default audit and the interaction map is `05_docs/Open_Questions_Register_2026-08-19.md`.
Golden-set labels tagged `depends_on_olq` keep the tag as a mark of permanent dependence.


---

## EVIDENCE APPENDED — 2026-08-19 (acquisition of primary judgments; questions remain open)

**OLQ-1:** *Union of India v. K.A. Najeeb* is now ON DISK from the Supreme Court's own API
(SOURCES.md entry 13, SHA-256 recorded). The "secondary summaries only — do not cite"
caution is lifted to "primary on disk, citable once read in full". *Badshah Majid Malik* is
also on disk (entry 12) — and the primary corrects the project's date: the operative order
is **18 October 2024** (Oka & Masih JJ), not 27 December 2024 as every project document
said from secondary sources; the bail was granted on the ONE-THIRD threshold. CLAUDE.md §3
still carries the wrong date and is flagged for Abhishek's edit.

**OLQ-4:** *Satender Kumar Antil* is now on disk (entry 11, judiciary-mirror provenance
caveat recorded). Its own guideline list defines Category C as "Offences punishable under
Special Acts containing stringent provisions for bail like NDPS (S.37), PMLA (S.45), UAPA
(S.43D(5), Companies Act, 212(6), etc." — **POCSO IS NOT NAMED**; the list is four statutes
plus "etc.", and para 64 expressly declines to deal with individual enactments. This is
primary-text evidence bearing on candidates (c) (the category describes an approach, not a
provision list) and (d) (POCSO's listing came from imprecise secondary summaries). Whether
POCSO stays in the gate-3 set is a legal-characterisation call and remains Abhishek's; the
register's "reading Antil would discriminate" prediction is hereby discharged — it did.


## OLQ-4 FACTUAL LIMB CLOSED — 2026-08-19 (appended)

The judgment itself answers the factual half of OLQ-4: **Satender Kumar Antil does not
place POCSO in Category C.** The Category C definition in the judgment's own guideline list
names four statutes plus "etc."; POCSO's placement in the project's documents came from
secondary summaries (candidate (d) confirmed as the mechanism of the listing, with (c)'s
reading of the category as approach-not-enumeration supported by para 64). What remains —
whether anything nonetheless warrants treating POCSO as Category C in practice, given
ss.29–30's presumptions — is a legal-characterisation question and is PERMANENTLY OPEN
like every question in this file. Coded behaviour: POCSO's flag stays on the restated basis
(D-054 correction); every report and filing carries the non-exhaustiveness line.

**RULED (Abhishek, 2026-08-26):** the (c)/(d) candidate choice is closed — the flag stays
on the restated four-part basis exactly as D-054's correction implemented it. Nothing
about this question awaits a ruling; the remaining limb stays permanently open like every
question in this file. Status tracked in `OPEN_ITEMS.yaml` (D-088).
