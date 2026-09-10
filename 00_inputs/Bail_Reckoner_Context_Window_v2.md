# Bail Reckoner — Context Window v2

**Purpose.** This file is the single briefing a new human team member or AI agent reads before
touching this project. It supersedes nothing — it *extends* the earlier project doc
`Bail_Reckoner_Context_Window` (v1, 12 Aug 2026), which remains valid for its panel review and
critique. This file records what has been **built, verified and decided** since.

**Written:** 12 August 2026 · **Stage:** abstract and documentation complete; no code written yet.

---

## 0. How to read this file

| Section | Status |
|---|---|
| §1 Hard constraints | **Ground truth.** Do not contradict. |
| §2 Verified legal ground truth | **Verified August 2026.** Citations in §9. Statutory text still needs gazette verification (see §8). |
| §3 Verified statistics | **Verified August 2026** with source and as-on date attached to every figure. |
| §4 Deliverables produced | Factual inventory of files. |
| §5 Design decisions now locked in | Decided; reversible. IDs map to `DECISIONS.md`. |
| §6 What changed from v1 | Corrections to v1 — read this if you have read v1. |
| §7 How to rebuild | Reproducible commands. |
| §8 NOT verified | **Read before asserting anything.** |
| §9 Sources | All 32 individually checked. |

---

## 1. Hard constraints (unchanged from v1)

1. **The problem statement is assigned, not chosen.** SIH1702, "Bail Reckoner", raised by the
   **Ministry of Law & Justice, Government of India**. Institute reference MLRS24-169. Neither the
   title nor the scope may be altered to manufacture novelty. Innovation lives in the *solution*.
2. **Honesty over polish.** Every claim must be traceable to a statute, a judgment, a dataset or a
   measurement. In a legal-domain project a fabricated citation is not a cosmetic error — it is
   the exact failure the domain fears most.
3. **The system is an assistive tool, not a decision-maker.** Hold that line in UI copy, report
   headers, the demo script and viva answers.
4. **No bail-outcome prediction.** The project computes a statutory entitlement. It does not
   predict what a judge will do. This distinction is now stated explicitly in every deliverable.

---

## 2. Verified legal ground truth

### 2.1 Section 479 BNSS 2023 — quoted from bare-act reproductions, cross-checked

**479(1)** — *"Where a person has, during the period of investigation, inquiry or trial under this
Sanhita of an offence under any law (not being an offence for which the punishment of death or
life imprisonment has been specified as one of the punishments under that law) undergone detention
for a period extending up to one-half of the maximum period of imprisonment specified for that
offence under that law, he shall be released by the Court on bail."*

- **First proviso** — a **first-time offender** ("who has never been convicted of any offence in
  the past") shall be released **on bond** at **one-third** of the maximum period.
- **Second proviso** — the Court may, after hearing the Public Prosecutor and **for reasons
  recorded in writing**, order continued detention beyond one-half, or release on **bail bond**
  instead of bond.
- **Third proviso** — no person shall in any case be detained for longer than the maximum period
  prescribed for the offence.

> ⚠️ **v1 correction.** v1 §4.1 described the *third* proviso as the one permitting extension
> beyond the half-way mark. That is the **second** proviso. The third proviso is the absolute cap.
> Get this right in the decision table.

**479(2)** — *"Notwithstanding anything in sub-section (1), and subject to the third proviso
thereof, where an investigation, inquiry or trial in more than one offence or in multiple cases
are pending against a person, he shall not be released on bail by the Court."*

- No equivalent existed in s.436A CrPC.
- **Applied**: *K. Ramakrishna v. Assistant Director, Directorate of Enforcement*, High Court of
  Karnataka, Crl. P. No. 9930/2024, decided **23 November 2024** — s.479(1) is "subject to Section
  479(2)" and the provisions "have to be read conjointly".
- This is the **most important single provision in the project.** An engine that computes the
  fraction but ignores 479(2) returns confident false positives for a large share of real
  undertrials.

**479(3)** — *"The Superintendent of jail, where the accused person is detained, on completion of
one-half or one-third of the period mentioned in sub-section (1), as the case may be, shall
forthwith make an application in writing to the Court to proceed under sub-section (1) for the
release of such person on bail."*

- A named officer, a computable moment, a required document. **This is the strongest single
  feature available inside the problem statement.** Auto-drafting this application requires no
  judicial discretion and is directly aligned with the MHA advisory of 24 October 2024, which
  directs Jail Superintendents to prefer such applications.

### 2.2 Satender Kumar Antil v. CBI (11 July 2022) — the rules-engine backbone

| Category | Scope |
|---|---|
| **A** | Offences punishable with imprisonment of 7 years or less, not falling in B or D |
| **B** | Offences punishable with death, life imprisonment, or more than 7 years |
| **C** | Special Acts with stringent bail provisions — NDPS s.37, PMLA s.45, UAPA s.43-D(5), Companies Act s.212(6), POCSO |
| **D** | Economic offences not covered by special Acts |

Bail is the rule, jail the exception. This maps almost one-to-one onto a rules engine.

### 2.3 Section 479 and special statutes

*Badshah Majid Malik v. Directorate of Enforcement*, Crl. A. No. 4258/2024, Supreme Court,
**27 December 2024** (Oka and Masih JJ) — s.479(1) BNSS **applies to prosecutions under the PMLA**.
Reported as also treating the provision as available to persons already in custody before
1 July 2024. **Treat the precise scope of retrospective operation as contested and evolving** —
it is still being worked out through *In Re: Inhuman Conditions in 1382 Prisons*
(W.P. (C) 406/2013) and executive circulars. Make it a configurable, cited assumption in the
engine, not a hard-coded constant.

### 2.4 Executive and judicial push on implementation

- **Supreme Court, 22 October 2024** (Roy and Bhatti JJ) — directed States/UTs to take proactive
  steps to release deserving undertrials under s.479.
- **MHA Advisory No. 17013/20/2024-PR, 24 October 2024** — special campaign on Constitution Day
  (26 November 2024); Jail Superintendents to prefer applications on completion of the prescribed
  periods; explicit exclusion of heinous offences where death or life imprisonment is prescribed;
  States/UTs to report in a prescribed proforma.

---

## 3. Verified statistics — always cite with the as-on date

### NCRB *Prison Statistics India 2024* (as on 31 December 2024)

| Figure | Value |
|---|---|
| Total inmates | **5,11,542** |
| Sanctioned capacity | **4,53,769** |
| Jails | **1,333** |
| National occupancy | **112.7%** (a decade low) |
| Undertrials | **3,71,440** — about **72.6%** |
| Convicts | ~26.6% |
| Most overcrowded | Delhi **194.6%**, then Meghalaya **163.5%** |
| Undertrials held over 5 years without conviction | **9,028** (2.4% of undertrials) |

> ⚠️ **v1 correction.** v1 §4.2 cited Delhi at "~200%". That is PSI 2023 reporting.
> **PSI 2024 says 194.6%.** Use the newer figure.

### Section 479 BNSS implementation (as on 26 November 2024)

| Figure | Value |
|---|---|
| Prisoners identified as eligible, all States/UTs | **951** |
| Granted bail by a court | **334** |
| Share of the undertrial population even identified | **0.26%** |

Top States: West Bengal 297 identified / 98 bailed; Maharashtra 153 / 22; Uttar Pradesh 110 / 51.

**This is the single most useful statistic the project has.** It converts "the entitlement is
under-realised" from an assertion into a measurement, and it is exactly the gap the tool addresses.
Source: PIB PRID 2117796 (MHA written reply, Rajya Sabha, 2 April 2025) and the matching
data.gov.in dataset.

### Published Indian bail-prediction baselines (a *different* task — do not present as our target)

| System | Corpus | Best accuracy |
|---|---|---|
| HLDC multi-task (Findings of ACL 2022) | 912,568 UP district-court docs; 176,849 bail docs | **0.80** (0.78 F1) |
| IBPS fine-tuned Phi-4 + QLoRA (arXiv:2508.07592) | 150,430 High Court bail judgments, 5 HCs | **0.79** |
| IBPS baseline | same | 0.47 |
| IBPS baseline + naive RAG | same | **0.33** |

**The last row matters most.** Adding retrieval naively *reduced* accuracy from 0.47 to 0.33.
Retrieval augmentation is not free. Measure it; do not assume it helps.

---

## 4. Deliverables produced (12 August 2026)

| File | What it is |
|---|---|
| `Abstract_Proforma_FILLED_BailReckoner.docx` | **Primary.** MLRITM Registration/Abstract Proforma, filled. All original field labels preserved verbatim. |
| `Abstract_Proforma_FILLED_BailReckoner.doc` | Legacy-format copy. Lower fidelity than the .docx. |
| `Abstract_Proforma_FILLED_BailReckoner.pdf` | Print/review copy. |
| `Bail_Reckoner_Extended_Abstract.docx` / `.pdf` | 9-page extended abstract in the C9 style, with §2 statutory framework, §6 evaluation plan, §7 related work, §9 responsible-AI position, §10 known limitations, §12 references (32 sources). |
| `Bail_Reckoner_Project_Presentation.pptx` | 19-slide deck. Native PowerPoint charts, four custom diagrams, speaker notes, references slide. |
| `DECISIONS.md` | Decision log, D-001 … D-024, plus open items O-1 … O-5. |
| `Bail_Reckoner_Context_Window_v2.md` | This file. |
| `make_diagrams.py` · `build_abstract.js` · `build_deck.js` · `fill_proforma.py` | Regeneration scripts. |

### Proforma contents as filled

| Field | Value |
|---|---|
| Academic Year / Batch / Program | 2026-27 · 2023-27 · B.Tech *(pre-filled in template)* |
| Regulation / Year-Sem | MLRS-R22 · IV-I *(pre-filled)* |
| Project Batch No | **9** |
| Roster | 1 Vallamalla Abhishek Prakash `237Y1A66C5` · 2 Revuru Arya `237Y1A66CD0` · 3 Modhumpally Arvind `237Y1A66C9` · 4 Boru Vimala `237Y1A66I3` — all Dept **CSM** |
| Guide | **BLANK — team to fill (O-1)** |
| Title | AI-Powered "Bail Reckoner" — An Intelligent Legal Assistance System for Streamlining Bail Eligibility and Application |
| Type | **Application** (marked bold+underline; full option list preserved) |
| MLRS-PS ID / SIH ID / Bucket | MLRS24-169 · SIH1702 · Smart Automation (Category: Software) |
| Abstract | Five labelled sections + keywords |

---

## 5. Design decisions now locked in

These are load-bearing. Changing one changes the project's defensibility.

| ID | Decision |
|----|----------|
| **D-009** | **Discretionary factors are never scored.** Flight risk and witness influence are an unweighted checklist reproduced verbatim for a human. This also removes the main fairness-audit surface. |
| **D-010** | **No "ineligible" output state.** The negative case is *"no statutory entitlement identified on these inputs — human review required"*, with every gate that fired shown. Asymmetric error costs → asymmetric design. |
| **D-011** | **"No unified tool exists" is rescoped**: ICJS, e-Prisons/BOMS, FASTER, UTRCs and e-Courts move records and orders; **none computes entitlement**. Position the project as feeding UTRCs and discharging s.479(3). |
| **D-012** | **No bail-outcome prediction.** Explicitly distinguished from HLDC and IBPS. |
| **D-008** | **Statutory text must be verified against the official gazette before encoding.** Quoted text carries this caveat. |
| **D-017** | Published prediction accuracies are shown **with a warning label** that they measure a different task. |

### The gate order the engine must implement

1. Death or life imprisonment prescribed? → **bar** (s.479(1) main clause)
2. More than one offence, or multiple cases, pending? → **bar** (s.479(2))
3. Special-statute bail bar? → **bar / blocking condition** (*Antil* Category C)
4. First-time offender? → **selects the fraction**, ⅓ on bond vs ½ on bail. **Not a bar.**
5. Custody ≥ applicable threshold? → yes: entitlement established, generate the s.479(3)
   application. No: not yet entitled; compute the qualifying date and schedule recomputation.

> Gate 2 is evaluated **before** any threshold arithmetic is reported.

---

## 6. What changed from Context Window v1

| Item | v1 said | Correct position |
|---|---|---|
| s.479 provisos | "Third proviso: detention may be extended beyond the half-way mark" | That is the **second** proviso. The third is the absolute cap. |
| Delhi occupancy | "~200%" (PSI 2023) | **194.6%** per PSI 2024. |
| Prison totals | PSI 2023 figures (5,30,333 / 120.8%) | PSI 2024: **5,11,542 / 112.7% / 3,71,440 undertrials**. |
| s.479 implementation numbers | Not present | **951 identified / 334 bailed as on 26.11.2024.** Now the headline statistic. |
| SIH1702 official text | "not retrieved" | **Partially resolved.** Confirmed in the SIH 2024 list: ID SIH1702, Organisation Ministry of Law & Justice, Title "Bail Reckoner", Category Software, Theme SmartAutomation. The extended description is still not retrieved (O-4). |
| Related work | Not covered | HLDC, IBPS, IL-TUR now cited with figures, and the distinction from this project stated. |
| Special statutes × s.479 | Not covered | *Badshah Majid Malik v. ED* (SC, 27 Dec 2024): s.479(1) applies to PMLA prosecutions. |
| 479(2) case law | Not covered | *K. Ramakrishna v. ED* (Karnataka HC, 23 Nov 2024). |

**v1's panel review (§6), gap table (§7) and recommended next actions (§8) remain valid and are
still the best guide to what to build.** Nothing in this file contradicts them.

---

## 7. How to rebuild the deliverables

Working directory contains all scripts. Dependencies: `python-docx`, `matplotlib`, `pillow`
(pip); `docx`, `pptxgenjs` (npm, preinstalled); LibreOffice; Poppler.

```bash
python3 fill_proforma.py                       # → Abstract_Proforma_FILLED_BailReckoner.docx
python3 make_diagrams.py                       # → diag_*.png  (run BEFORE build_deck.js)
node build_abstract.js                         # → Bail_Reckoner_Extended_Abstract.docx
node build_deck.js                             # → Bail_Reckoner_Project_Presentation.pptx

# PDF + page images for visual QA
soffice --headless --convert-to pdf <file>
pdftoppm -jpeg -r 110 <file>.pdf page
```

To change a statistic, edit it in **all four** places: `build_abstract.js` (§1 and §12),
`build_deck.js` (slides 2, 3, 19), `make_diagrams.py` (`manual_chain` footer) and this file.
There is no single source of truth for the numbers yet — **creating one is a worthwhile first
engineering task.**

---

## 8. NOT verified — read before asserting

- **The verbatim official text of Section 479 BNSS has not been read from the gazette.** The text
  in §2.1 comes from bare-act reproductions cross-checked against four secondary commentaries.
  It is good enough to write an abstract from. **It is not good enough to encode a decision table
  from.** Read the official text first.
- **The extended official description of SIH1702** was not retrieved. Only the list entry
  (ID, organisation, title, category, theme) is confirmed. Get the full text from `sih.gov.in`.
- **The precise scope of s.479's retrospective application is unsettled** and evolving through the
  *1382 Prisons* proceedings and executive circulars. Do not state it as settled.
- **`237Y1A66CD0`** (Revuru Arya) is 11 characters where the other three roll numbers are 10, and
  was supplied only after an earlier value collided with the team lead's. **Verify it.**
- **MLRITM reference MLRS24-169** is taken from the C9 abstract; not independently verifiable.
- **The guide's name is unknown.** The `.doc` metadata names *Dr. Srinivas Bachu* as document
  author — that is almost certainly the template creator, not this project's guide.
- **No implementation exists.** No repository, dataset, prototype or golden set. Every accuracy
  figure in the deliverables is either a cited third-party result or a stated *plan*, never a claim
  about this system.
- **NCRB PSI 2024 figures beyond those in §3 were not individually verified.**
- **State-level s.479 figures** (WB 297/98 etc.) come from the PIB annexure via a secondary read;
  confirm against the data.gov.in dataset before using them in a submitted document.
- **The claim that the C9 abstract has or has not been formally submitted is unknown** (O-3).

---

## 9. Sources

All 32 checked individually on 12 August 2026. None dead, none mismatched. Four
(three Indian Kanoon pages, one data.gov.in dataset) refuse automated fetching but were confirmed
as correct canonical addresses by search.

**Statute and case law**

- [Section 479 BNSS — bare-act text](https://www.apnilaw.com/bare-act/bnss/section-479-bharatiya-nagarik-suraksha-sanhita-bnss-maximum-period-for-which-under-trial-prisoner-can-be-detained/)
- [Section 479 BNSS — Indian Kanoon](https://indiankanoon.org/doc/87702491/)
- [Satender Kumar Antil v. CBI (11 July 2022) — Indian Kanoon](https://indiankanoon.org/doc/7148380/)
- [Satender Kumar Antil v. CBI — 2022 LiveLaw (SC) 577, full PDF](https://www.livelaw.in/pdf_upload/577-satender-kumar-antil-v-central-bureau-of-investigation-11-july-2022-425458.pdf)
- [Bail or Jail — Categories A–D explained, Cyril Amarchand](https://corporate.cyrilamarchandblogs.com/2022/08/bail-or-jail-the-supreme-court-clarifies-the-law-and-lays-down-the-guidelines/)
- [K. Ramakrishna v. Directorate of Enforcement — Karnataka HC order PDF](https://images.assettype.com/barandbench-kannada/2024-11-27/bv7yccdh/K_Ramakrishna_Vs_ED.pdf)
- [Case note on the Karnataka HC ruling (s.479(1) subject to s.479(2))](https://www.lawweb.in/2025/07/karnataka-hc-no-bail-us-4791-bnss-on.html)
- [Badshah Majid Malik v. ED — s.479 applies to PMLA prosecutions](https://knallp.com/supreme-court-settles-the-applicability-of-section-479-of-bnss-to-pmla-prosecutions-badshah-majid-malik-vs-ed/)
- [In Re: Inhuman Conditions in 1382 Prisons, order of 23 August 2024](https://indiankanoon.org/doc/4389693/)
- [Law Commission of India, Report No. 268 (May 2017)](https://taxguru.in/wp-content/uploads/2017/06/Report-No.268.pdf)

**Commentary on s.479**

- [When Exceptions Swallow The Rule — LiveLaw](https://www.livelaw.in/articles/when-exceptions-swallow-rule-problem-section-479-bnss-307288)
- [Analysing the remedy of bail under s.479 BNSS — Bar & Bench](https://www.barandbench.com/columns/analysing-the-remedy-of-bail-under-section-479-of-bnss)
- [Drishti Judiciary — s.479 BNSS](https://www.drishtijudiciary.com/editorial/section-479-bnss)
- [Maximum detention of an undertrial — iPleaders](https://blog.ipleaders.in/maximum-detention-of-an-undertrial-and-release-section-479-bnss/)

**Government, policy and data**

- [MHA Advisory No. 17013/20/2024-PR, 24 October 2024 (PDF)](https://www.mha.gov.in/sites/default/files/PrisonBNSS_25102024.pdf)
- [PIB — Release of Prolonged Under-Trial Prisoners (951 / 334 as on 26.11.2024)](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2117796)
- [data.gov.in — State/UT-wise eligible prisoners under s.479 as on 26-11-2024](https://www.data.gov.in/resource/stateut-wise-number-eligible-prisoners-identified-and-granted-bail-court-under-provisions)
- [MHA — Rajya Sabha Unstarred Q. 1039, 4 December 2024 (PDF)](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2024-pdfs/RS04122024/1039.pdf)
- [SC directs proactive release under s.479 — LiveLaw, 22 October 2024](https://www.livelaw.in/top-stories/take-proactive-steps-to-release-deserving-undertrial-prisoners-under-s479-bnss-statesuts-273246)
- [NCRB Prison Statistics India 2024 — analysis](https://www.drishtiias.com/daily-updates/daily-news-analysis/prison-statistics-india-report-2024)
- [PSI 2024 figures — Daily Excelsior](https://www.dailyexcelsior.com/indias-prisons-reach-112-7-pc-occupancy-in-2024-delhi-tops-at-194-6-pc-over-3-71-lakh-undertrials/)
- [NALSA to SC — undertrials in jail despite bail](https://www.deccanherald.com/india/5000-undertrial-prisoners-in-jail-despite-being-granted-bail-only-1417-released-nalsa-to-sc-1186583.html)
- [Digital Personal Data Protection Act, 2023 — official text (MeitY)](https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf)

**Digital criminal-justice infrastructure**

- [FASTER — SC directs acceptance of e-authenticated bail orders](https://www.livelaw.in/top-stories/faster-release-of-prisoners-after-bail-supreme-court-directs-statesuts-to-accept-e-authenticated-copies-of-orders-182327)
- [Allahabad HC directions on ICJS implementation — SCC Online](https://www.scconline.com/blog/post/2025/12/20/allahabad-hc-issues-directions-for-implementation-of-inter-operable-criminal-justice-system/)

**Research and datasets**

- [HLDC: Hindi Legal Documents Corpus — Findings of ACL 2022 (PDF)](https://aclanthology.org/2022.findings-acl.278.pdf)
- [HLDC dataset and code — Exploration-Lab, GitHub](https://github.com/Exploration-Lab/HLDC)
- [IBPS: Indian Bail Prediction System — arXiv:2508.07592](https://arxiv.org/html/2508.07592v2)
- [IL-TUR: Benchmark for Indian Legal Text Understanding and Reasoning — arXiv:2407.05399](https://arxiv.org/html/2407.05399v1)
- [Predictive Modeling for Bail Applications Using IndicBERT and HLDC — Springer](https://link.springer.com/chapter/10.1007/978-981-96-5265-5_42)

**Problem statement**

- [Smart India Hackathon — official portal](https://sih.gov.in/)
- [SIH 2024 consolidated problem-statement list (entry SIH1702)](https://www.driems.ac.in/wp-content/uploads/2024/08/SIH_2024_PS.pdf)

---

## 10. If you are the next agent, do these four things first

1. **Read the official gazette text of Section 479 BNSS** and write the decision table from it —
   all of 479(1), the three provisos, 479(2) and 479(3). This artefact carries the project.
2. **Create a single source of truth for the statistics** (a small YAML/JSON file with value,
   source URL and as-on date) and have the documents read from it. Right now the same figure lives
   in four files.
3. **Build the golden test set** — 150–200 cases with legally verified expected outputs, with
   deliberate coverage of 479(2) multiple-case scenarios, death/life exclusions, first-time-offender
   ⅓ cases, special-statute bars and transitional IPC/BNS cases. Without it there is no defensible
   accuracy claim.
4. **Build the s.479(3) application generator.** It is inside the problem statement, legally
   sanctioned, needs no judicial discretion, and demonstrates the whole project in ten seconds.

Then re-read v1 §7 (gap table) and v1 §8 (recommended actions). They still hold.
