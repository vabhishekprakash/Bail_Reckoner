# Cross-channel reconciliation — text layer vs OCR (2026-08-29)

**CLAIM CLASS: cross-channel agreement measurement. This is NOT a verification and
NOT an accuracy figure — two machine channels agreeing can both be wrong, and their
agreement binds nothing. It is never blended with Tier 1, Tier 2, the retrieval
measurements, the Layer B floor or the self-scored sheet. No value from either
channel enters the penalty database; only a human's page-reading does (D-046), and
no row is verified or promoted by this document (Abhishek's item 4, 2026-08-29).**

Channel A: the stored text-layer extraction (`extractor_output_do_not_rely_on`).
Channel B: OCR over rasterised pages (pypdfium2 -> RapidOCR, D-089) — it never
touches the PDF text layer, so the text channel's documented failure modes
(intra-word spaces, page-break truncation, heading misfires on embedded text,
state-amendment run-on) cannot occur in it; it has its own instead.
Compared facets, one shared parser over both channels: term maxima ('may extend
to N'), mandatory minima ('shall not be less than N'), life/death punishment
mentions, and the limb count (`count_punishment_limbs`).

Sections compared: 41 (86 queue rows) - **agree 26 - disagree 13 - OCR could not read 2**
Agreement rate over readable sections: **26/39 = 0.667** (claim class above; unreadable sections excluded from the
denominator and listed in full below — exclusion stated, not hidden).

The reviewer's use of this document: disagreement rows are where the two machines
cannot both be right — read those pages first. Agreement rows still get read;
agreement only means the page-reading is unlikely to be fighting an extraction
artefact.

## Disagreements (read these pages first)

### IPC_1860 s.304A — facets: minima
* rows in queue: 1 - source: `IPC_1860_Act45_IndiaCode_repealed_file.pdf` - IPC_1860_Act45_IndiaCode_repealed_file.pdf, printed p. 75 (PDF page index 74), s.304A
* Channel A (text layer): maxima [24m, 84m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 1
* Channel B (OCR):        maxima [24m, 84m] - minima [84m] - life mentioned: True - death mentioned: False - limb count: 1
* page image cropped to the section: `cross_channel_crops_2026-08-29/IPC_1860-304A_p74.png`
* OCR pages consumed (0-based): [74]

### BNS_2023 s.331 — facets: maxima
* rows in queue: 8 - source: `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` - BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf, printed page unknown (PDF page index 90), s.331
* Channel A (text layer): maxima [24m, 36m, 36m, 60m, 120m, 120m, 120m, 168m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 8
* Channel B (OCR):        maxima [36m, 36m, 60m, 120m, 120m, 120m, 168m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 8
* page image cropped to the section: `cross_channel_crops_2026-08-29/BNS_2023-331_p90.png`
* OCR pages consumed (0-based): [90, 91]

### BNS_2023 s.318 — facets: maxima
* rows in queue: 3 - source: `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` - BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf, printed p. 86 (PDF page index 85), s.318
* Channel A (text layer): maxima [36m, 60m, 84m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 3
* Channel B (OCR):        maxima [36m, 60m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 3
* page image cropped to the section: `cross_channel_crops_2026-08-29/BNS_2023-318_p85.png`
* OCR pages consumed (0-based): [85, 86]

### BNS_2023 s.351 — facets: maxima
* rows in queue: 3 - source: `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` - BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf, printed page unknown (PDF page index 96), s.351
* Channel A (text layer): maxima [24m, 24m, 84m, 84m] - minima [none found] - life mentioned: True - death mentioned: True - limb count: 3
* Channel B (OCR):        maxima [24m, 24m, 84m] - minima [none found] - life mentioned: True - death mentioned: True - limb count: 3
* page image cropped to the section: `cross_channel_crops_2026-08-29/BNS_2023-351_p96.png`
* OCR pages consumed (0-based): [96, 97]

### IPC_1860 s.506 — facets: maxima, life/death mentions, limb count
* rows in queue: 3 - source: `IPC_1860_Act45_IndiaCode_repealed_file.pdf` - IPC_1860_Act45_IndiaCode_repealed_file.pdf, printed p. 118 (PDF page index 117), s.506
* Channel A (text layer): maxima [24m, 84m, 84m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 3
* Channel B (OCR):        maxima [24m, 84m] - minima [none found] - life mentioned: False - death mentioned: True - limb count: 2
* page image cropped to the section: `cross_channel_crops_2026-08-29/IPC_1860-506_p117.png`
* OCR pages consumed (0-based): [117]

### IPC_1860 s.448 — facets: maxima
* rows in queue: 1 - source: `IPC_1860_Act45_IndiaCode_repealed_file.pdf` - IPC_1860_Act45_IndiaCode_repealed_file.pdf, printed p. 107 (PDF page index 106), s.448
* Channel A (text layer): maxima [12m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* Channel B (OCR):        maxima [none found] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* page image cropped to the section: `cross_channel_crops_2026-08-29/IPC_1860-448_p106.png`
* OCR pages consumed (0-based): [106]

### NDPS_1985 s.21 — facets: maxima, minima
* rows in queue: 3 - source: `NDPS_1985_Act61_IndiaCode_asOn_2022-01-03.pdf` - NDPS_1985_Act61_IndiaCode_asOn_2022-01-03.pdf, printed p. 17 (PDF page index 16), s.21
* Channel A (text layer): maxima [240m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 0
* Channel B (OCR):        maxima [120m, 240m] - minima [120m] - life mentioned: False - death mentioned: False - limb count: 0
* page image cropped to the section: `cross_channel_crops_2026-08-29/NDPS_1985-21_p16.png`
* OCR pages consumed (0-based): [16]

### NDPS_1985 s.22 — facets: maxima
* rows in queue: 3 - source: `NDPS_1985_Act61_IndiaCode_asOn_2022-01-03.pdf` - NDPS_1985_Act61_IndiaCode_asOn_2022-01-03.pdf, printed p. 17 (PDF page index 16), s.22
* Channel A (text layer): maxima [120m, 240m] - minima [120m] - life mentioned: False - death mentioned: False - limb count: 0
* Channel B (OCR):        maxima [240m] - minima [120m] - life mentioned: False - death mentioned: False - limb count: 0
* page image cropped to the section: `cross_channel_crops_2026-08-29/NDPS_1985-22_p16.png`
* OCR pages consumed (0-based): [16, 17]

### BNS_2023 s.105 — facets: minima
* rows in queue: 2 - source: `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` - BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf, printed p. 34 (PDF page index 33), s.105
* Channel A (text layer): maxima [120m, 120m] - minima [60m] - life mentioned: True - death mentioned: False - limb count: 2
* Channel B (OCR):        maxima [120m, 120m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 2
* page image cropped to the section: `cross_channel_crops_2026-08-29/BNS_2023-105_p33.png`
* OCR pages consumed (0-based): [33]

### IPC_1860 s.304 — facets: maxima
* rows in queue: 2 - source: `IPC_1860_Act45_IndiaCode_repealed_file.pdf` - IPC_1860_Act45_IndiaCode_repealed_file.pdf, printed p. 74 (PDF page index 73), s.304
* Channel A (text layer): maxima [120m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 2
* Channel B (OCR):        maxima [120m, 120m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 2
* page image cropped to the section: `cross_channel_crops_2026-08-29/IPC_1860-304_p73.png`
* OCR pages consumed (0-based): [73, 74]

### BNS_2023 s.191 — facets: maxima
* rows in queue: 2 - source: `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` - BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf, printed page unknown (PDF page index 54), s.191
* Channel A (text layer): maxima [24m, 60m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 2
* Channel B (OCR):        maxima [24m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 2
* page image cropped to the section: `cross_channel_crops_2026-08-29/BNS_2023-191_p54.png`
* OCR pages consumed (0-based): [54]

### BNS_2023 s.85 — facets: maxima
* rows in queue: 1 - source: `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` - BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf, printed page unknown (PDF page index 28), s.85
* Channel A (text layer): maxima [36m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* Channel B (OCR):        maxima [none found] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* page image cropped to the section: `cross_channel_crops_2026-08-29/BNS_2023-85_p28.png`
* OCR pages consumed (0-based): [28]

### IPC_1860 s.471 — facets: limb count
* rows in queue: 1 - source: `IPC_1860_Act45_IndiaCode_repealed_file.pdf` - IPC_1860_Act45_IndiaCode_repealed_file.pdf, printed p. 110 (PDF page index 109), s.471
* Channel A (text layer): maxima [none found] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* Channel B (OCR):        maxima [none found] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 0
* page image cropped to the section: `cross_channel_crops_2026-08-29/IPC_1860-471_p109.png`
* OCR pages consumed (0-based): [109]

## OCR could not read

### BNS_2023 s.115
* rows in queue: 1 - source: `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` - BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf, printed p. 38 (PDF page index 37), s.115
* reason: section start found on page index 37 but the next section's heading never appeared within 3 further pages — a truncated read is a failed read, not a result (pages tried, 0-based: [37, 38, 39, 40])

### BNS_2023 s.126
* rows in queue: 1 - source: `BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf` - BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf, printed page unknown (PDF page index 40), s.126
* reason: heading '126.' not found by OCR on page index 40 or 41 (pages tried, 0-based: [40, 41])

## Agreements

* IPC_1860 s.379 (1 row(s)) — both channels: maxima [36m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* NDPS_1985 s.20 (3 row(s)) — both channels: maxima [120m, 120m, 240m] - minima [120m] - life mentioned: False - death mentioned: False - limb count: 0
* BNS_2023 s.324 (5 row(s)) — both channels: maxima [6m, 12m, 24m, 60m, 60m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 5
* BNS_2023 s.316 (4 row(s)) — both channels: maxima [60m, 84m, 84m, 120m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 4
* BNS_2023 s.103 (3 row(s)) — both channels: maxima [none found] - minima [none found] - life mentioned: True - death mentioned: True - limb count: 3
* BNS_2023 s.106 (3 row(s)) — both channels: maxima [24m, 60m, 120m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 3
* BNS_2023 s.309 (3 row(s)) — both channels: maxima [84m, 120m, 120m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 3
* BNS_2023 s.303 (3 row(s)) — both channels: maxima [36m, 60m] - minima [12m] - life mentioned: False - death mentioned: False - limb count: 3
* IPC_1860 s.302 (1 row(s)) — both channels: maxima [none found] - minima [none found] - life mentioned: True - death mentioned: True - limb count: 1
* IPC_1860 s.323 (1 row(s)) — both channels: maxima [12m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.341 (1 row(s)) — both channels: maxima [1m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.392 (1 row(s)) — both channels: maxima [120m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.420 (1 row(s)) — both channels: maxima [84m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.426 (1 row(s)) — both channels: maxima [3m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.406 (1 row(s)) — both channels: maxima [36m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* BNS_2023 s.317 (4 row(s)) — both channels: maxima [36m, 36m, 120m, 120m] - minima [none found] - life mentioned: True - death mentioned: False - limb count: 4
* BNS_2023 s.109 (3 row(s)) — both channels: maxima [120m] - minima [none found] - life mentioned: True - death mentioned: True - limb count: 3
* BNS_2023 s.117 (3 row(s)) — both channels: maxima [84m, 84m] - minima [120m] - life mentioned: True - death mentioned: False - limb count: 3
* IPC_1860 s.307 (2 row(s)) — both channels: maxima [120m] - minima [none found] - life mentioned: True - death mentioned: True - limb count: 2
* BNS_2023 s.137 (1 row(s)) — both channels: maxima [84m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* BNS_2023 s.340 (1 row(s)) — both channels: maxima [none found] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.147 (1 row(s)) — both channels: maxima [24m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.325 (1 row(s)) — both channels: maxima [84m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.363 (1 row(s)) — both channels: maxima [84m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.411 (1 row(s)) — both channels: maxima [36m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1
* IPC_1860 s.498A (1 row(s)) — both channels: maxima [36m] - minima [none found] - life mentioned: False - death mentioned: False - limb count: 1

---
Generated by scratchpad driver over `bail_reckoner.statutes.ocr_channel` (D-089);
RapidOCR 1.4.4, pypdfium2 5.13.0, render scale 3.0. Deterministic given the same
wheels and PDFs (the PDFs' SHA-256 are integrity-tested in the suite).
