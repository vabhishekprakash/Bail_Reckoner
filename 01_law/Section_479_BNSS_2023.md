# Section 479, Bharatiya Nagarik Suraksha Sanhita, 2023 (Act No. 46 of 2023) — gazette text

**Status: VERIFIED against the official gazette. This file is the project's canonical s.479
text.** Where any other project document disagrees with this file, this file governs; where this
transcription and the stored PDFs disagree, the PDFs govern.

## Provenance

**Primary source (original gazette):**
- File: `BNSS_2023_Act46_Gazette_2023-12-25_MHA.pdf` (this directory)
- SHA-256: `5E60E2AFE30D0FE7ECA4F8126301146B76C86A444E690581F81EB564843517FE`
- Retrieved: **2026-08-12** from
  `https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf`
  (Ministry of Home Affairs, Government of India)
- Document: The Gazette of India, EXTRAORDINARY, Part II—Section 1, No. 54, New Delhi, Monday,
  December 25, 2023 / Pausha 4, 1945 (Saka). Registered No. DL—(N)04/0007/2003—23. Ministry of
  Law and Justice (Legislative Department). "The following Act of Parliament received the assent
  of the President on the 25th December, 2023…" — THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023,
  **No. 46 of 2023**. 249 PDF pages; **s.479 appears on printed gazette page 144 (PDF page 144,
  0-based index 143)**.

**Cross-check source (consolidated text):**
- File: `BNSS_2023_Act46_IndiaCode_asOn_2025-10-06.pdf` (this directory)
- SHA-256: `54B27A4F2786DC5867C2CC23391E8359B3B29125684119ACBC652D1630A716D6`
- Retrieved: **2026-08-12** from
  `https://www.indiacode.nic.in/bitstream/123456789/20099/1/A202346.pdf`
  (India Code, Legislative Department) — "The Bharatiya Nagarik Suraksha Sanhita, 2023 (ACT NO.
  46 OF 2023) [As on the 6th October, 2025]". 282 PDF pages; s.479 spans printed pages 161–162
  (PDF 0-based indices 160–161).
- **Cross-check result (2026-08-12): the operative text of s.479 is character-identical between
  the two sources** after normalizing whitespace and stripping page-number artifacts (1,644
  operative characters compared). The consolidated as-on-2025-10-06 text shows **no amendment to
  s.479 since enactment.** Both government sites refuse automated fetching (HTTP 403 to tooling);
  retrieval succeeded with a standard browser user-agent — noted for reproducibility.

Transcription below was extracted programmatically (pypdf 6.15.0) from the primary source and
cleaned only of layout artifacts (line breaks, page headers/footers, spacing inside tokens). A
human eyeball-check against gazette page 144 is recommended at first `01_law\` review.

---

## Verbatim text

**Marginal note:** *Maximum period for which undertrial prisoner can be detained.*

> **479.** (1) Where a person has, during the period of investigation, inquiry or trial under
> this Sanhita of an offence under any law (not being an offence for which the punishment of
> death or life imprisonment has been specified as one of the punishments under that law)
> undergone detention for a period extending up to one-half of the maximum period of imprisonment
> specified for that offence under that law, he shall be released by the Court on bail:
>
> Provided that where such person is a first-time offender (who has never been convicted of any
> offence in the past) he shall be released on bond by the Court, if he has undergone detention
> for the period extending up to one-third of the maximum period of imprisonment specified for
> such offence under that law:
>
> Provided further that the Court may, after hearing the Public Prosecutor and for reasons to be
> recorded by it in writing, order the continued detention of such person for a period longer
> than one-half of the said period or release him on bail bond instead of his bond:
>
> Provided also that no such person shall in any case be detained during the period of
> investigation, inquiry or trial for more than the maximum period of imprisonment provided for
> the said offence under that law.
>
> *Explanation.*—In computing the period of detention under this section for granting bail, the
> period of detention passed due to delay in proceeding caused by the accused shall be excluded.
>
> (2) Notwithstanding anything in sub-section (1), and subject to the third proviso thereof,
> where an investigation, inquiry or trial in more than one offence or in multiple cases are
> pending against a person, he shall not be released on bail by the Court.
>
> (3) The Superintendent of jail, where the accused person is detained, on completion of one-half
> or one-third of the period mentioned in sub-section (1), as the case may be, shall forthwith
> make an application in writing to the Court to proceed under sub-section (1) for the release of
> such person on bail.

---

## Diff against the pre-M0 project text (CLAUDE.md §3 / brief §2.1, "cross-checked bare-act
reproductions") — every discrepancy, per D-008

1. **479(1) main clause — VERBATIM MATCH.** (Terminal punctuation only: gazette ends the clause
   with ":" leading into the provisos; the project text quoted it with ".".)
2. **First proviso — substance match; project text was a summary.** Gazette wording the summary
   omitted: "released on bond **by the Court**", "**for the period** extending up to one-third",
   "specified for **such** offence". The load-bearing parenthetical "(who has never been
   convicted of any offence in the past)" matches verbatim. ⅓ + bond confirmed.
3. **Second proviso — substance match; one nuance.** Gazette: "for reasons **to be recorded by
   it** in writing… release him on bail bond **instead of his bond**". The "instead of his bond"
   phrasing ties the bail-bond alternative to the *bond* route — phrasing the summaries dropped.
   Interpretive weight, if any, is a Tier-2 question; no arithmetic impact.
4. **Third proviso — substance match.** Gazette adds "**during the period of investigation,
   inquiry or trial**" — the cap is expressly on under-trial detention. Confirmed as the absolute
   cap (gate 0, D-034).
5. **⚠️ THE EXPLANATION — ABSENT from every pre-M0 project document** (CLAUDE.md §3, brief §2.1,
   deck slide 4): *"In computing the period of detention under this section for granting bail,
   the period of detention passed due to delay in proceeding caused by the accused shall be
   excluded."* **This changes the custody arithmetic directly** (gates 0 and 5): detention
   attributable to accused-caused delay is excluded from the computation. It requires an input
   the system did not previously model (excluded periods) and raises a legal-operational
   question (what counts as accused-caused delay, and who determines it) — logged as **OLQ-7**;
   engine handling proposed as a Step-2 decision.
6. **479(2) — VERBATIM MATCH.**
7. **479(3) — VERBATIM MATCH.**
8. **Marginal note** ("Maximum period for which undertrial prisoner can be detained") — not
   previously recorded in any project document.
9. **Act number:** BNSS is **Act No. 46 of 2023** (assent 25 Dec 2023). No project document had
   asserted an act number; now on record. (Act 45 of 2023 is the Bharatiya Nyaya Sanhita.)

**Bottom line:** the pre-M0 quotations of 479(1) main clause, 479(2) and 479(3) were exact; the
provisos were faithful summaries; **the omission of the Explanation was the single substantive
gap, and it is precisely the kind of discrepancy D-008 existed to catch.**
