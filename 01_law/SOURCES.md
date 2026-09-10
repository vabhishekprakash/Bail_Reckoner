# `01_law\` — statutory sources and their provenance

Source-of-truth legal texts. Every penalty row in `02_data\` must cite one of these files by name
and page (CLAUDE.md §6: a row without provenance does not enter the database). **Nothing in this
directory may be superseded by a blog, a commentary, a community dataset, or model memory** (C5).

Acquired 2026-08-12 (session 2). Append as sources are added; record rejections too — knowing
which official-looking source is defective is worth as much as knowing which is good.

---

## ACCEPTED — use these

### 1. `BNSS_2023_Act46_Gazette_2023-12-25_MHA.pdf` — **primary for s.479**
- **SHA-256** `5E60E2AFE30D0FE7ECA4F8126301146B76C86A444E690581F81EB564843517FE` · 2,033,181 bytes · 249 pages
- Retrieved 2026-08-12 from `https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf`
- The Gazette of India, EXTRAORDINARY, Part II—Sec. 1, No. 54, New Delhi, 25 December 2023 /
  Pausha 4, 1945 (Saka). **Bharatiya Nagarik Suraksha Sanhita, 2023 — Act No. 46 of 2023.**
- **s.479 at gazette page 144** (PDF page index 143). Canonical transcription and the full
  pre/post-verification diff: `Section_479_BNSS_2023.md`.

### 2. `BNSS_2023_Act46_IndiaCode_asOn_2025-10-06.pdf` — cross-check for s.479
- **SHA-256** `54B27A4F2786DC5867C2CC23391E8359B3B29125684119ACBC652D1630A716D6` · 1,948,217 bytes · 282 pages
- Retrieved 2026-08-12 from `https://www.indiacode.nic.in/bitstream/123456789/20099/1/A202346.pdf`
- Consolidated text "[As on the 6th October, 2025]". s.479 spans printed pages 161–162.
- **Cross-check result: operative s.479 text character-identical to the gazette** (1,644 chars
  compared, whitespace and page-number artifacts normalized) → s.479 unamended since enactment.

### 3. `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` — **primary for BNS maximum sentences**
- **SHA-256** `C9DA896E7A16C481A46235789F74F545B7A9ED7F3A5C8049D0B1B9252C6731F4` · 1,324,200 bytes · 102 pages
- Retrieved 2026-08-12 from `https://www.mha.gov.in/sites/default/files/250883_english_01042024.pdf`
- **Bharatiya Nyaya Sanhita, 2023 — Act No. 45 of 2023**, assent 25 December 2023.
- Carries an **embedded digital-signature block** naming the Government of India Press
  (`o=Government of India Press`, `ou=Deputy Manager`, signed 2023-12-25 21:11:37 +05:30) —
  the strongest provenance of any file here. Signature validity has **not** been cryptographically
  verified by this project; the block's presence is what is recorded.

### 4. `BNS_2023_Act45_IndiaCode_asOn_2025-10-06.pdf` — cross-check for BNS
- **SHA-256** `FF92DCC72778944011807644B6033B1140DDBE6D7E9F82AC32FD419DAE03AA86` · 896,392 bytes · 112 pages
- Retrieved 2026-08-12 from `https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf`
- Consolidated "[As on the 6th October, 2025]". Includes Statement of Objects and Reasons.
- **Not yet cross-checked section-by-section against the gazette** — that is an M1 task, done per
  offence as each row is verified.

### 5. `IPC_1860_Act45_IndiaCode_repealed_file.pdf` — **primary for IPC maximum sentences (transitional cases)**
- **SHA-256** `AE8920AD726FBB6DFDEC8D327C4BDDA580CA175BCAD1EF4212CA868FE4D1EA3A` · 1,104,850 bytes · 119 pages
- Retrieved 2026-08-12 from `https://www.indiacode.nic.in/repealedfileopen?rfilename=A1860-45.pdf`
- **Indian Penal Code, 1860 — Act No. 45 of 1860**, served from India Code's *repealed acts*
  collection, i.e. the text as carried at repeal by BNS on 1 July 2024.
- **Currency verified by probe:** contains ss.354A, 354D, 376E, 166A (inserted by the Criminal
  Law (Amendment) Act, 2013) and ss.376AB, 376DA (2018); amending Acts referenced up to **2019**.
  This is the copy to use for offences committed before 1 July 2024.
- **Caveat:** the file carries no printed "as on" date. Its currency is inferred from the
  amendments present, not from a stated consolidation date. Marked `[UNVERIFIED]` on that
  narrow point; each IPC row is verified individually at M1 regardless.

### 6. `NDPS_1985_Act61_IndiaCode_asOn_2022-01-03.pdf` — gate 3, NDPS s.37
- **SHA-256** `8CD8E71F5E1BD5A5D98A414D553C76838AE8BF9B493097981220305EF70DEAC2` · 609,101 bytes · 54 pages
- Retrieved 2026-08-12 from
  `https://www.indiacode.nic.in/bitstream/123456789/18974/1/narcotic-drugs-and-psychotropic-substances-act-1985.pdf`
- Narcotic Drugs and Psychotropic Substances Act, 1985; "Last Update 3-1-2022".
- **s.37 verified at printed p. 25** (PDF page index 24): the twin-condition bar —
  s.37(1)(b)(ii) permits bail only where, the Public Prosecutor opposing, "the court is satisfied
  that there are reasonable grounds for believing that he is not guilty of such offence and that
  he is not likely to commit any offence while on bail"; s.37(2) makes these limitations
  additional to those under the CrPC. Decision table now carries `provision_verified: true`.

### 7. `POCSO_2012_Act32_IndiaCode_asOn_2023-02-28.pdf` — gate 3, and the OLQ-4 evidence
- **SHA-256** `DEF90F072FDB6B62FE95ADAFA0F5E1EF08F5F1002DBB6067F8AF4B1CD94A5C5B` · 207,723 bytes · 17 pages
- Retrieved 2026-08-12 from `https://www.indiacode.nic.in/bitstream/123456789/2079/1/AA2012-32.pdf`
- Protection of Children from Sexual Offences Act, 2012 (Act 32 of 2012); "Last update
  28-02-2023", so post-2019-amendment.
- **Finding: the Act contains no twin-condition bail bar.** The word "bail" occurs **exactly
  once** in the whole Act — in **s.31**, which *applies* the CrPC "including the provisions as to
  bail and bonds" to Special Court proceedings. None of the s.37 markers appear anywhere. This
  is a reading of the bare act (Tier 1); *why* POCSO is nonetheless in *Antil* Category C is a
  Tier-2 question left open in OLQ-4.

- **COMPLETENESS PROOF for that negative (run 2026-08-12).** A negative finding is only as good
  as the completeness of the text it was read from, and two IPC PDFs already rejected below
  looked complete and were not. Checks performed on the stored file:
  - **17 of 17 pages yield extractable text; none is blank.**
  - The Act's **own arrangement-of-sections table lists 46 sections, numbered 1..46 with no gaps
    in the sequence.**
  - **Every one of those 46 listed sections is present in the body text** (whitespace-collapsed
    match), so no section is listed-but-missing.
  - On that verified-complete text, "bail" still occurs **once**, and none of
    `shall not be released on bail` / `reasonable grounds for believing` /
    `not guilty of such offence` appears anywhere.
  - *Caveat recorded honestly:* the phrase "notwithstanding anything contained in the Code of
    Criminal Procedure" **does** occur, but not in a bail context — the sole bail provision is
    s.31, and s.31 *applies* the CrPC rather than overriding it.
  - *Method note:* a first attempt used a line-start regex and reported 8 false "gaps", including
    s.31 itself — the very section already read and quoted. Those were PDF line-wrap artifacts.
    The check above compares the Act's own contents table against the body instead, which is why
    it is trustworthy where the first was not.

### 8. `UAPA_1967_Act37_MHA_amended_to_2019.pdf` — gate 3, UAPA s.43-D(5)
- **SHA-256** `15201C51C6E8168EB22245296353B38BA1F63BB17ECDDE52689A4A8021EAC98F` · 462,441 bytes · 28 pages
- Retrieved 2026-08-12 from `https://www.mha.gov.in/sites/default/files/A1967-37.pdf`
- **s.43-D(5) verified at PDF page index 20.** Structurally **different** from NDPS s.37 and
  PMLA s.45: those require a positive finding of probable *innocence* before bail may be granted;
  s.43-D(5) instead bars bail where the court, "on a perusal of the case diary or the report made
  under section 173 of the Code", finds "the accusation against such person is prima facie true".
  Also note **s.43-D(4)**: s.438 CrPC (anticipatory bail) is excluded altogether.
- **Currency caveat:** no printed "as on" date; amendments to 2019 inferred from content.

### 9. `PMLA_2002_Act15_IndiaCode_amended_to_2019.pdf` — gate 3, PMLA s.45(1)
- **SHA-256** `D3699F0228F7B9CDF8311F9E8998032FB15E6570070B99A578ECA3CB8FCD6413` · 504,120 bytes · 47 pages
- Retrieved 2026-08-12 from `https://www.indiacode.nic.in/bitstream/123456789/2036/5/A2003-15.pdf`
- **s.45(1) verified**, twin conditions present and quoted in the decision table.
- **Currency check performed, because s.45 has a strike-down-and-re-enactment history.** The
  stored text shows the opening words of s.45(1) carrying a **substitution footnote marker**
  (`1[Notwithstanding anything contained in the Code … shall be released on bail or on his own
  bond unless—]`), with `2[under this Act]` separately marked — i.e. this **is** a
  post-re-enactment text, not the struck-down original. Amendment footnotes reference Acts up to
  **23 of 2019**.
- **Caveat:** the document carries **no printed "as on" date**; currency is inferred from the
  footnote apparatus, exactly as for the stored IPC. Re-check before use in a submitted document.

---

### 10. `CompaniesAct_2013_Act18_IndiaCode_amended_to_2021.pdf` — gate 3, Companies Act s.212(6)
- **SHA-256** `D6E286D2A3FEEC89A7D432A5A572E91AF9F0135411B03E57F72B7A8EF72139AF` · 3,281,971 bytes · 370 pages
- Retrieved 2026-08-19 from `https://www.indiacode.nic.in/bitstream/123456789/2114/5/A2013-18.pdf`
- **s.212(6) verified at PDF page index 141** (the s.212 heading opens on index 140). Twin
  conditions present — the NDPS s.37 / PMLA s.45 structure (probable-innocence finding required
  before bail), NOT the UAPA inversion — plus a first proviso permitting bail for a person
  under sixteen, a woman, or the sick or infirm if the Special Court so directs, and a second
  proviso confining cognizance to a written complaint by the SFIO Director or an authorised
  Central Government officer.
- **Scope, and it matters:** the sub-section's opening words carry a substitution footnote —
  `1[offence covered under section 447]`, **Subs. by Act 21 of 2015, s. 17 (w.e.f.
  29-5-2015)** — so post-2015 the bar attaches to the s.447 fraud offence, not to the wider
  pre-amendment list. A charge under any other Companies Act section does not engage s.212(6)
  on this text.
- **Currency caveat:** no printed "as on" date anywhere in the 370 pages (checked by scan; the
  two "as on" phrases in the body are statutory language, not a currency stamp). Amendment
  footnotes reference Acts up to **2021** (Acts of 2015, 2016, 2017, 2018, 2019, 2020 and 2021
  all appear), so currency is inferred from the apparatus, exactly as for the stored IPC and
  PMLA. Re-check before use in a submitted document.

### 11. `SatenderKumarAntil_v_CBI_SC_2022-07-11_sciAPI.pdf` — the Category C authority, now PRIMARY
- **UPGRADED 2026-09-02** per this entry's own standing instruction ("upgrade this entry if
  it is [located]"). The Supreme Court's own copy was found via the 21-Jan-2025 compliance
  order in the same case (diary 37889/2022, which confirmed the case chain) and a search on
  the API's URL pattern.
- **SHA-256** `525BF579E85CFDD3DE1DA9BF97E53FD5F214C7452AD8520AEA1DCFA96BF88955` · 402,825 bytes · 85 pages
- Retrieved 2026-09-02 from
  `https://api.sci.gov.in/supremecourt/2021/27955/27955_2021_5_1505_36261_Judgement_11-Jul-2022.pdf`
  — **the Supreme Court's own API: primary.** Diary 27955/2021. "CORRECTED REPORTABLE" print;
  no aggregator footer; all 85 pages extract text.
- **Content verified on upgrade:** the Category C definition appears with wording identical
  to the mirror's ("...Companies Act, 212(6), etc.") and para 64 ("SPECIAL ACTS (CATEGORY
  C)") expressly declines to deal with individual enactments — the D-054 correction and the
  standing non-exhaustiveness note both survive the upgrade unchanged.
- **Superseded mirror, kept on disk for the record:**
  `SatenderKumarAntil_v_CBI_SC_2022-07-11_MPHCJA_mirror.pdf`, SHA-256
  `60B9E3AFB509136E151FD13AF8EEC651D00D211C982565BB6680542A23DB09DA` · 399,412 bytes ·
  61 pages, retrieved 2026-08-19 from
  `https://mpsja.mphc.gov.in/Joti/pdf/LU/Satender_Kumar_Antil_vs_Central_Bureau_Of_Investigation_on_11_July_2022.PDF`
  (MP High Court Judicial Academy hosting of an Indian Kanoon print). Nothing built on the
  mirror is invalidated by the upgrade; which file the precedent corpus reads is a recorded
  decision, not a silent swap.
- *Satender Kumar Antil v. CBI*, MA 1849/2021 in SLP(Crl) 5191/2021, judgment 11 July 2022
  (Kaul & Sundresh JJ, Sundresh J authoring).
- **Content verified on acquisition:** the guideline categories appear verbatim — Category C:
  "Offences punishable under Special Acts containing stringent provisions for bail like NDPS
  (S.37), PMLA (S.45), UAPA (S.43D(5), Companies Act, 212(6), etc." — and para 64 ("SPECIAL
  ACTS (CATEGORY C)") expressly declines to deal with individual enactments.
- **OLQ-4 finding: POCSO is NOT named in the judgment's own Category C list.** Its membership
  in this project's gate-3 set rests on secondary summaries. Bears directly on OLQ-4
  candidates (c)/(d); **RULED by Abhishek 2026-08-26** — the flag stays on the restated
  four-part basis of D-054's correction (see OPEN_ITEMS.yaml).

### 12. `BadshahMajidMalik_v_ED_SC_Order_2024-10-18_sciAPI.pdf` — s.479 applies to PMLA
- **SHA-256** `3B7FA7F6279756993473DC1330919F6AAAB40F69EFEE21E6277E86626AEF8F87` · 74,817 bytes · 6 pages
- Retrieved 2026-08-19 from `https://api.sci.gov.in/supremecourt/2024/33383/33383_2024_6_13_56499_Order_18-Oct-2024.pdf`
  — **the Supreme Court's own API: primary.**
- *Badshah Majid Malik v. Directorate of Enforcement*, SLP(Crl) 10846/2024 (leave granted),
  diary 33383/2024, **Order dated 18 October 2024** (Oka & Masih JJ). Holds s.479(1) BNSS
  applies to PMLA prosecutions (s.436A CrPC post-dates the PMLA; the corresponding s.479(1)
  therefore applies); bail granted on the ONE-THIRD threshold.
- **DATE CORRECTION established by the primary:** the project's records said "Crl. A. No.
  4258/2024, 27 December 2024" (CLAUDE.md §3, the register, OLQ-1) — a secondary-source
  date. No 27-Dec-2024 order exists in the indexed record; 18 October 2024 is the operative
  date. Exactly the failure class that motivated acquiring primaries (the gazette
  Explanation precedent). CLAUDE.md §3's line is flagged for Abhishek's edit.

### 13. `UnionOfIndia_v_KANajeeb_SC_2021-02-01_sciAPI.pdf` — the OLQ-1 lead, now primary
- **SHA-256** `9DC6762EDF19E580A934DB2E6DCF926527412C01005DAB84E2AE73AB51A8CCB3` · 391,909 bytes · 14 pages
- Retrieved 2026-08-19 from `https://api.sci.gov.in/supremecourt/2019/40158/40158_2019_32_1501_25867_Judgement_01-Feb-2021.pdf`
  — **the Supreme Court's own API: primary.**
- *Union of India v. K.A. Najeeb*, Crl.A. 98/2021 (from SLP(Crl) 11616/2019), REPORTABLE,
  judgment 1 February 2021 (Ramana, Surya Kant, Bose JJ). OLQ-1's caution now lifts one
  notch: the judgment itself is on disk and citable once read in full; the register's
  "secondary summaries only" caveat is superseded by this entry.

### PERMANENTLY UNACQUIRED — *K. Ramakrishna v. Assistant Director, ED* (Karnataka HC, Crl.P. 9930/2024)
- **Closed as permanently unacquired by Abhishek's ruling, 2026-08-26.** The Karnataka High
  Court's judgment portal is a captcha-gated search with no directly linkable PDF, and no
  .gov.in-hosted copy surfaced. Acquisition FAILED at primary; no aggregator copy is
  substituted, ever. The citation discipline already recorded stands permanently: every
  citation of this judgment in this project is secondary-sourced and says so, and gate 2
  stands on the statutory text of s.479(2), not on this case.

## REJECTED — do not use; recorded so nobody re-downloads them

### `https://www.indiacode.nic.in/bitstream/123456789/6853/1/unlawful_activities_prevention_act1967.pdf`
**The un-amended 1967 text.** 14 pages, and — decisively — **zero occurrences of the word
"bail"** and no s.43D at all, that section having been inserted by the 2008 amendment. This is
the most dangerous rejection recorded here, because it would not have produced an obvious error:
it would have produced a **false `VERIFIED_ABSENT` for UAPA**, the exact mirror of the *true*
`VERIFIED_ABSENT` for POCSO, and the two are indistinguishable without checking whether the text
is current. The lesson is that a negative finding requires a currency check as well as a
completeness check. Use the MHA copy (entry 8).

### `https://www.indiacode.nic.in/bitstream/123456789/15354/1/ndpsact.pdf`
**Not the Act.** Despite the filename `ndpsact.pdf` on an India Code bitstream path, this is the
**Law Commission of India's 155th Report** on narcotic drugs — a scanned document whose OCR text
is badly garbled ("lJA\\V (.~OMMISSI().N ()1{ INDIA"). Third official-looking source in this
project to be defective, and the second whose *filename* actively misleads.

### `https://www.indiacode.nic.in/bitstream/123456789/11091/1/the_indian_penal_code,_1860.pdf`
**Incomplete: covers only ss.1–120.** 58 pages. Reaches s.511 at the very end but every offence
chapter in between is missing — no s.302 (murder), no s.379 (theft), no s.376 (rape), no
s.392 (robbery). Verified by mapping section coverage page by page. Looks entirely legitimate at
a glance; it is the single most dangerous file encountered in this session, because a penalty
table built from it would silently omit the most commonly charged offences.

### `https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf`
**Complete but badly stale.** 227 pages, all chapters present, *but* s.376(1) carries the
pre-2013 wording ("not less than seven years but which may be for life or for a term which may
extend to ten years") and ss.354A, 354D, 376E, 166A are absent entirely. Latest amending Act
referenced: **1997**. Using it would yield wrong maxima for sexual offences and stalking — the
error would be invisible without checking, because the document is otherwise well-formed.

### `https://thc.nic.in/Central%20Governmental%20Acts/Indian%20Penal%20Code,%201860%20.pdf`
**Scanned images, no text layer.** 56.5 MB, 226 pages, 1 character extractable. Unusable for
programmatic extraction; would require OCR, which D-026 puts out of scope.

---

## Retrieval note (reproducibility)

Both `mha.gov.in` and `indiacode.nic.in` return **HTTP 403 to default tooling user-agents**.
Retrieval succeeded with a standard desktop browser user-agent string. This is a site policy,
not an access restriction on the documents, which are public. Downloads were performed with
PowerShell `Invoke-WebRequest -UserAgent`.

## Still needed

*(Rewritten 2026-08-26 — the previous version of this section had gone stale, still listing
the special statutes and two judgments as outstanding after all were acquired. A stale
"still needed" misstates the acquisition state on the file that exists to state it.)*

- **BNSS s.359** (compounding of offences) for D-036 criterion (vi). The only statutory text
  still outstanding.
- **POCSO barring provision:** nothing to acquire — `VERIFIED_ABSENT` against the stored Act
  (no bail-restriction section exists to fetch); OLQ-4's remaining limb is the *basis* of
  POCSO's Category-C membership, a ruling, not a document.
- **Upgrade path for entry 11 (*Antil*):** still open. Retried at the Supreme Court's own
  hosting on 2026-08-26 (web search over api.sci.gov.in / digiscr.sci.gov.in): the judgment's
  diary-numbered PDF was not located — only later compliance orders in diary 37889/2022
  surfaced. The API URL pattern needs the original diary number, which the search does not
  yield. The judiciary-mirror copy (Indian Kanoon print lineage) remains the stored text;
  upgrade the entry if the sci.gov.in original is ever located.
- ~~Special statutes for gate 3~~ — **done**: NDPS, PMLA, UAPA, Companies Act all acquired
  and verified (entries above). ~~*Antil*, *Badshah Majid Malik*~~ — **done** (entries 11–12).
  *K. Ramakrishna* — **closed as permanently unacquired** (block above).
