# Open Questions Register — Bail Reckoner: what the system does where the law is unsettled

**Prepared:** 19 August 2026 · **Project:** AI-Powered Bail Reckoner (SIH1702, Ministry of Law &
Justice; MLRS24-169), B.Tech major project, MLRIT Hyderabad · **Maintained by:** Vallamalla
Abhishek Prakash (team lead)

---

## What this is

This system computes an undertrial prisoner's **statutory entitlement to release under Section
479 of the Bharatiya Nagarik Suraksha Sanhita, 2023**, shows the arithmetic, and cites the
provision behind every step. It predicts nothing, scores nothing discretionary, and decides
nothing — every output is routed to a human and carries an unsigned "Legally reviewed by" field.

**This register is a statement of what the system does where the law is unsettled, and what
would change under each reading.** It is not a request to a lawyer, and it is not legal advice
to a client — there is no client and no live case behind any entry. **No advocate review is
available to this project, permanently** (recorded 19 August 2026): every question below is
open and unresolvable within the project, and the coded behaviour each entry describes is the
system's permanent behaviour, not an interim default awaiting an answer. Where the law is
genuinely unsettled, the system's response is abstention — a `CONTESTED` flag routed to human
review — never a silently chosen reading.

Every question states: **(a)** what the engine does — permanently, **(b)** the readings
available, **(c)** what would change in the computation under each reading, and **(d)** the
direction of error each way. Direction of error matters because the project's design rule is
asymmetric: a false "entitled" is caught by the court that hears the application; a false "not
entitled" silently keeps a person in custody and nobody appeals a machine's silence. The
dangerous direction is therefore always the one that under-claims.

**The statutory text used throughout** is the gazette text of s.479 BNSS 2023 (Gazette of India
Extraordinary, Part II—Sec. 1, No. 54, 25 Dec 2023, p. 144), cross-checked character-identical
against India Code as on 6 October 2025. Full text with provenance:
`01_law/Section_479_BNSS_2023.md`.

---

## Part I — The two structural questions (L-series)

### L-001 — Does "the maximum period of imprisonment specified for that offence" attach to the *section*, or to the *charge as framed*?

**(a) Today.** The penalty database is keyed one row per **punishment limb** — `(regime,
section, variant)` — because a single section routinely carries several maxima selected by case
facts: quantity bands (NDPS), capacity of the accused (criminal breach of trust gradations),
victim age, repeat conviction (BNS s.303(2)'s second-conviction limb), degree of harm. Where the
charged limb is not identified, the engine **abstains** (`OFFENCE_NOT_IN_DATABASE`) rather than
picking one.

**(b) Readings.** (i) "That offence" = the section: one maximum per section, the highest limb
governs. (ii) "That offence" = the offence as charged: the limb invoked by the charge-sheet
governs, and the limb is a required input.

**(c) What changes.** Reading (i): the per-limb keying collapses; the highest limb's maximum is
used without asking which limb is charged. Reading (ii): current build stands. No schema is
neutral between them — a one-row-per-section model silently answers (i).

**(d) Direction of error.** A maximum **too high** (e.g. the highest limb applied to a
lesser-limb charge) inflates the release threshold *and* suppresses the absolute-cap alarm —
the silent under-claim. A maximum **too low** produces an over-claim the court catches. The
current abstention-on-unknown-limb avoids both at the cost of answering fewer cases.

### L-002 — Is a section's prescribed maximum uniform across States?

**(a) Today.** The engine has **no State dimension**. Sections whose stored text carries an
inline `STATE AMENDMENTS` block (found so far: IPC s.304A, where Himachal Pradesh's s.304-AA
prints life imprisonment against the central two years; and IPC s.379) are flagged
`STATE_AMENDMENT_UNASSESSED`: the report says an amendment exists and has not been evaluated,
and asserts nothing about its effect.

**(b) Readings.** (i) The central enactment's maximum governs everywhere (the amendment creates
a distinct offence charged separately, or does not displace the maximum). (ii) The maximum is a
function of the State of prosecution.

**(c) What changes.** Reading (i): the flag is dropped with the reason recorded. Reading (ii):
the engine needs a State input, penalty rows need a jurisdiction key, and every stored report
must name the State it was computed for — this multiplies with L-001's limb dimension.

**(d) Direction of error — both ways, unusually.** A true State maximum **higher** than the
recorded one → threshold understated → over-claim (court catches it). A true State maximum
**lower** → threshold overstated **and** the absolute cap suppressed → the silent under-claim.
Because the error runs both directions, there is no conservative default to hide behind; hence
the flag rather than a chosen reading.

---

## Part II — The cap, and which maximum governs (OLQ-11, OLQ-2, OLQ-9a)

These three are L-001's "what does 'the offence' attach to" question surfacing at three
different levels. They interact: an answer to L-001 will usually imply answers here, and the
gate-0 contested band exists only while OLQ-11 is open.

### OLQ-11 — Does the third-proviso cap measure against each charged offence's own maximum, or the highest among the charges?

The third proviso: *"no such person shall in any case be detained during the period of
investigation, inquiry or trial for more than the maximum period of imprisonment provided for
the said offence under that law."*

**(a) Today.** The cap is computed against **both bounds**. Custody at or past the *highest*
charged maximum → `DETAINED_BEYOND_MAXIMUM` (the most urgent condition the system reports,
surfaced above everything else). Custody at or past the *lowest* charged maximum but below the
highest → `CONTESTED_CAP_BASIS`, routed to human review. Neither reading is adopted.

**(b) Readings.** (i) Per offence: the cap fires the moment custody passes *any* charged
offence's maximum. (ii) Governing maximum: detention is justified by the gravest charge, so
only the highest maximum caps.

**(c) What changes.** Answer (i): the band collapses downward — the contested flag becomes the
urgent flag at the lowest crossed maximum. Answer (ii): the band collapses upward — the
contested flag is dropped.

**(d) Direction of error.** Reading (ii) makes the urgent alarm fire as late as it possibly
can — and this matters most in multi-case situations, because **s.479(2) is expressly "subject
to the third proviso"**, so for a person barred by the multiple-case rule the cap is the *only*
surviving route to relief. A larger governing number here looks conservative while suppressing
the one protection left. Reading (i) over-alarms at worst, costing a human review.

### OLQ-2 — With several offences charged, which maximum governs the person-level threshold?

**(a) Today.** Per-offence arithmetic is displayed for every charge; the person-level
entitlement threshold uses the **highest** maximum among charged offences (the longest
threshold — the reading that never overstates an entitlement). Marked unverified.

**(b) Readings.** Per-offence entitlement; gravest-charge; or something else (e.g. the offence
for which remand is currently authorised).

**(c) What changes.** The aggregation function and the report's person-level threshold line;
per-offence rows are unaffected.

**(d) Direction of error.** The highest-maximum rule can only delay the computed entitlement —
safe against over-claiming, but it under-claims for anyone whose lesser charge would already
qualify them if lesser charges count.

### OLQ-9a — Does the third-proviso cap reach an offence excluded from s.479(1) by the death/life carve-out?

**(a) Today.** The cap is computed and its flag raised **regardless** of the death/life
exclusion: a person charged with a death/life offence still gets the cap checked against any
co-charged term offence.

**(b) Readings.** (i) The proviso sits inside s.479(1) and shares its exclusion, so no cap for
excluded offences. (ii) The proviso's "in any case" is general.

**(c) What changes.** Reading (i): the cap is suppressed where the death/life bar fires.
Reading (ii): current behaviour confirmed and citable.

**(d) Direction of error.** Suppressing wrongly is the silent under-claim; flagging wrongly
costs a human review. The current behaviour over-flags at worst.

---

## Part III — The multiple-case bar (OLQ-5, OLQ-3)

**Citation discipline note (2026-08-19; closed 2026-08-26):** *K. Ramakrishna v. Assistant
Director, ED* (Karnataka HC, Crl.P. 9930/2024) is **PERMANENTLY UNACQUIRED** — closed by
Abhishek's ruling of 2026-08-26 (captcha-gated primary, no aggregator substitution ever;
SOURCES.md records the closure). The project's reliance on it — s.479(1) read subject to
s.479(2), conjointly — rests on a case note; the citation must not imply the judgment was
read, permanently. Gate 2 stands on the statutory text of s.479(2) regardless.

### OLQ-5 — Does a single FIR charging multiple sections trigger s.479(2)?

s.479(2): *"…where an investigation, inquiry or trial in more than one offence or in multiple
cases are pending against a person, he shall not be released on bail by the Court."*

**(a) Today.** Default NARROW: the bar fires on multiple *cases*. A single case charging
several sections is flagged `CONTESTED` and routed to human review — never silently cleared,
never silently barred. Both readings are implemented and switchable. The contested state also
blocks the s.479(3) application generator: no filing is generated on a reading the project has
declined to choose.

**(b) Readings.** Broad ("more than one offence" reaches a multi-section FIR — noting that
multi-section FIRs are the norm, this reading risks the exception swallowing the rule) versus
narrow (the bar needs multiple cases).

**(c) What changes.** The default configuration is set to the authoritative reading; the
contested flag narrows accordingly; multi-section-single-FIR cases either proceed to the
threshold or are barred, with the holding cited.

**(d) Direction of error.** Broad wrongly applied = under-claim for the largest class of real
undertrials. Narrow wrongly applied = over-claim the court catches. The abstention avoids both
and answers neither.

### OLQ-3 — Does the s.479(2) bar ("released on bail") reach the first proviso's *bond* route?

**(a) Today.** The bar is treated as reaching both routes; affected first-time multi-case
persons are flagged `CONTESTED` and routed to review.

**(b) Readings.** (i) "Bail" is used loosely and the bar covers bond release too. (ii) The
words differ deliberately — s.479(2) bars *bail*, and a first-time offender's *bond* route
survives it.

**(c) What changes.** Answer (i): the flag is removed; bar confirmed for both. Answer (ii):
multi-case first-time offenders proceed to the one-third threshold, holding cited — the class
the project most wants to surface.

**(d) Direction of error.** Treating the bar as reaching bond, wrongly, under-claims for
first-time offenders specifically; the reverse over-claims.

---

## Part IV — Special statutes and gate 3 (OLQ-1, OLQ-4, OLQ-8)

The system never treats a special-statute bar as terminal: the s.479 arithmetic is always
computed and displayed, the applicable provision named and quoted verbatim from the stored bare
act, and the case routed to human review. All four *Satender Kumar Antil* Category-C bars are
now read and quoted from acquired official texts: NDPS s.37, PMLA s.45(1) (post-re-enactment
text, verified by its substitution footnote), UAPA s.43-D(5) (structurally inverted test:
prima-facie-true, not probable-innocence), Companies Act s.212(6) (post-2015 text: the bar
attaches only to the s.447 fraud offence). POCSO was read cover to cover and carries **no**
twin-condition bail bar.

### OLQ-1 — Does a Category-C bar qualify, or exclude, the s.479 entitlement? Does the NDPS position follow *Badshah* on PMLA?

**(a) Today.** *Badshah Majid Malik v. ED* (SC, Order 18 Oct 2024; date corrected against the primary, SOURCES.md 12) — s.479(1) applies to PMLA
prosecutions — is treated as settling PMLA only; NDPS/UAPA/Companies Act are treated as
unsettled, flagged, and routed. *Union of India v. K.A. Najeeb* (SC, 2021) is logged as a
**lead only**: reportedly the same architectural move (a Category-C bar yielding to an
independent release route), but constitutional (Article 21, delay) rather than statutory, and
this project has read only secondary summaries — it is cited in no output.

**(b) Readings.** s.479 as a freestanding entitlement overriding every twin-condition test;
or per-statute, each bar qualifying or excluding it.

**Scope note on the four bars** (each from the act's own text): NDPS s.37(1)(b) reaches
ss.19/24/27A and commercial-quantity offences only — two-thirds of the quantity-band rows
drafted under D-067 fall outside it; UAPA s.43-D(5) reaches Chapters IV and VI; Companies Act
s.212(6) reaches the s.447 fraud offence only. PMLA s.45(1) reads as the outlier — Act-wide,
"an offence under this Act" — but carries little practical risk: the Act's operative offence
is money-laundering under s.3 (verified in the stored text: "3. Offence of
money-laundering.—Whosoever..."), so a PMLA charge resolves in-scope nearly always.

**(c) What changes.** Statutes confirmed to follow *Badshah* get the holding cited in the
report; any statute authoritatively held to exclude s.479 gets a distinct, cited routing. The
flag-and-route behaviour itself does not change — the question governs what the report may
*say*, with what authority.

**(d) Direction of error.** Overstating a bar's reach under-claims; understating it produces a
filing the special court tests. The flag-not-bar design bounds both.

### OLQ-4 — On what basis is POCSO in Category C, when the Act contains no bail bar?

**(a) Today.** The Act was read (post-2019 text): "bail" appears exactly once, in s.31, which
*applies* CrPC bail provisions to Special Court proceedings. The system reports POCSO's
Category-C membership with the provision unresolved — on evidence, not for want of looking.

**(b) Candidate explanations** (none confirmable here): the ss.29–30 presumptions bear on bail
without being bars; co-charged IPC/BNS life offences carry the severity; Category C describes
practice, not text; or the listing is loose. **Reading *Antil* itself would discriminate among
these**; the judgment can be acquired and read without an advocate, and remains the single
highest-value acquisition outstanding for gate 3.

**(c) What changes.** Either the report names ss.29–30 as the basis, or POCSO leaves the
gate-3 set with the listing annotated — both one-line data edits.

**(d) Direction of error.** Keeping POCSO flagged costs a review; dropping it wrongly lets a
case through without the note. The current state over-flags at worst.

### OLQ-8 — Which statutes belong in the gate-3 set at all?

**(a) Today.** The *Antil* Category C list only — the list with judicial provenance. The
project's own earlier documents also floated the SC/ST Act and the IT Act; both are excluded,
with the exclusion recorded, because the SC/ST Act's s.18 bars *anticipatory* bail — a
different mechanism from a twin-condition bar on regular bail — and no Category-C listing
names either. A statute present on a charge but outside the set still surfaces:
"present, but no bail bar for it has been verified by this project."

**(b)–(c).** Confirm or amend the set; each addition requires the bare act acquired and its
provision quoted first.

**(d) Direction of error.** Wrong inclusion routes cases to review needlessly; wrong exclusion
lets a case through without the test attached — mitigated by the "present but unverified" line.

---

## Part V — The custody arithmetic (OLQ-6, OLQ-7, OLQ-9, OLQ-10)

### OLQ-6 — Arrest date or first-remand date?

**(a) Today.** Custody accrues from **date of arrest**; the first-remand date is also captured;
both are always displayed; divergence is flagged.
**(d)** Arrest-date counting yields the earlier qualifying date (over-claims at worst, by the
gap between the dates); remand-date counting under-claims by the same gap if wrong.

### OLQ-7 — What counts as "delay in proceeding caused by the accused" under the Explanation, and who determines it?

**(a) Today.** The engine takes an `excluded_days` input, **default zero, never computed by
the engine** — only a court-determined figure is accepted. Zero exclusions is the *maximum*
custody the person could claim, so a threshold not crossed at zero is not crossed under any
exclusion (never over-states); a threshold crossed at zero carries a printed caveat that a
real exclusion could uncross it.
**(b)** What qualifies (adjournments sought? absconding? frivolous applications?), whether it
must be judicially determined, and how it is evidenced on a jail record.
**(c)** The input's evidentiary requirements and the caveat's wording get grounded; the
default stays zero.

### OLQ-9 — Is the day of arrest itself a day of detention undergone?

**(a) Today.** **Inclusive** — the day of arrest counts, yielding the earlier qualifying date.
**(d)** Inclusive wrongly = one day's over-claim, court-tested; exclusive wrongly = one day's
silent under-claim on every computation.

### OLQ-10 — When a threshold falls part-way through a month, round or floor?

**(a) Today.** **Floor** (one-third of a ten-month maximum = 3 months + floor of ⅓ month),
with month-end overflow clamped down. Same asymmetry rationale as OLQ-9.
**(d)** Flooring wrongly = up to two days early (over-claim); ceiling wrongly = the same late
(silent under-claim).

---

## Part VI — Recently decided in-house; flag if wrong

**Pending offences only (D-072, decided 19 Aug 2026).** Gates 0, 1 and 5 now compute over
offences in *pending* cases only, on the reading that s.479(1) ties the period to an offence
under "investigation, inquiry or trial", which a concluded case is not. Before the change, a
concluded 20-year case could suppress the cap alarm for a person held past their pending
offence's maximum, and a concluded death/life case would have excluded s.479 for a pending
petty offence. Concluded cases still appear in reports, marked as taking no part.
Prior-conviction status is separately supplied and a concluded *conviction* still defeats
first-time status. **If this reading is wrong, say so** — it was decided by the team on the
statutory text, not by counsel.

---

## How the questions interact

* **L-001 → OLQ-11 → OLQ-2** are the same attachment question at limb, cap and person level.
  An answer of "the charge as framed" at L-001 tends toward per-offence at OLQ-11 and
  complicates the gravest-charge rule at OLQ-2; "the section" tends the other way. Answering
  L-001 first will likely compress the other two.
* **L-002 multiplies L-001.** If the maximum varies by State *and* by limb, the row key gains
  two dimensions at once.
* **A concrete instance of the two-level linkage exists: smoke case SMOKE-05.** It surfaced
  OLQ-11 (hand-labelled expecting the per-offence cap; the engine's governing-maximum rule
  disagreed, and the harness guard caught it on its first run) and its fact pattern also sits
  inside OLQ-2's threshold band (D-075), so it now carries `depends_on_olq: [OLQ-11, OLQ-2]`.
  One fact pattern exhibiting the same attachment question at two levels is what this map
  predicts.
* **OLQ-11 exists because of OLQ-2's rule.** The highest-maximum rule (safe for the release
  threshold) is the unsafe direction for the cap — one rule cannot be conservative for both.
  The gate-0 contested band is the holding pattern.
* **OLQ-5 × OLQ-3.** If the bar is broad (OLQ-5) *and* reaches bond (OLQ-3), first-time
  offenders with one multi-section FIR are barred entirely; if narrow and bail-only, they
  reach the one-third bond route. The four combinations produce materially different outcomes
  for the system's core beneficiary class.
* **OLQ-1 sits over gate 3 entirely**, and *Najeeb* (if it holds up on reading) and *Badshah*
  are the two known instances of bars yielding to independent routes.
* **s.479(2) is expressly subject to the third proviso**, so every cap question (OLQ-11,
  OLQ-9a, L-001, L-002) is also a question about the only relief route left to multi-case
  undertrials.

## Safe-default audit (19 August 2026)

With no resolution coming, the coded defaults are permanent behaviour, so each question was
audited: does the engine **flag to a human**, or **default to the reading that cannot silently
harm someone**? Result:

* **Flag-to-human (abstention):** OLQ-1 (gate 3 never terminal), OLQ-3 (bond route —
  CONTESTED), OLQ-4 (POCSO basis surfaced unresolved), OLQ-5 (single-FIR scope — CONTESTED),
  OLQ-11 (cap basis — contested band), the gate-3 scope question (D-074 — CONTESTED), and
  L-001's unknown-limb case (abstains via `OFFENCE_NOT_IN_DATABASE`).
* **Picked reading, erring only in the harmless (over-claim) direction, divergence flagged
  or de minimis:** OLQ-6 (arrest date, divergence flagged), OLQ-7 (zero exclusions, crossings
  caveated), OLQ-9 (inclusive day), OLQ-10 (floor), OLQ-9a (cap computed regardless —
  over-flags at worst), L-001's known-limb case (the charged limb, which can only under-state
  the maximum → over-claim, court-tested).
* **⚠ Finding 1 — OLQ-2: picked reading, unflagged, erring in the DANGEROUS direction.
  FIXED (D-075, approved and built 19 Aug 2026).** The person-level threshold uses the
  *highest* maximum among charged offences. That was chosen as "never overstates an
  entitlement" — but never-overstating is the under-claiming direction: a person whose lesser
  charge alone would qualify them (if per-offence aggregation is the correct reading) was
  reported NOT YET ENTITLED with a later date and no flag. As built: where a lower charged
  offence's own threshold has been crossed while the governing one has not,
  `CONTESTED_THRESHOLD_BASIS` is raised **and the report shows both qualifying dates** —
  governing-maximum and lowest-crossed — naming which aggregation rule yields which and that
  the question is unsettled. Not flag-only, deliberately: the qualifying date is the
  instruction a jail officer acts on, and a bare flag leaves them acting on the later date
  anyway. **This is the same conservatism inversion at a third level** — the cap (OLQ-11,
  D-066 band), the person-level threshold (OLQ-2, D-075 band), and limb attachment (L-001,
  where the per-limb abstention plays the equivalent role); tests and golden cases for the
  band carry `depends_on_olq: [OLQ-2, OLQ-11]` to keep the linkage queryable.
* **⚠ Finding 2 — L-002: a silent pick, promoted from residual (19 Aug 2026).** An
  undetectable State amendment is a silent pick of the uniformity reading:
  `STATE_AMENDMENT_UNASSESSED` fires only when an amendment block is detected in the stored
  text, so **the cases where the engine is confidently wrong are precisely the ones where
  nothing fires** — meeting neither audit criterion. Handled permanently, not conditionally:
  every report now carries a standing line that its maxima are taken from the central
  enactments and assume national uniformity, and that a State amendment absent from the
  stored consolidation cannot be detected. Per D-054's refinement — name the gap rather than
  let silence imply an answer; silence here implied uniformity, which nothing establishes.

## Standing consequences

The coded behaviour above is permanent. Golden-set labels tagged `depends_on_olq` remain
tagged — the tag now marks permanent dependence on an open question, not a pending
re-labelling. The underlying files — the verbatim gazette text, each question's full entry,
and every acquired bare act with its SHA-256 — are in the project repository.
