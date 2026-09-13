# Layer B extraction evaluation — deterministic baseline (2026-08-19)

**Claim class, stated wherever these figures travel: this measures a DETERMINISTIC
GAZETTEER OVER 38 KNOWN SECTIONS IN SYNTHETIC TEXT — a floor for a future model, not
charge-sheet extraction, and not the capability the Extended Abstract promises.**
(DPDP discipline: no real charge sheets exist anywhere in this project.) The synthetic
corpus does NOT represent real charge-sheet drafting — real inputs carry longer
citation chains, mixed regimes, vernacular forms and OCR noise — so recall here is
OPTIMISTIC. Fine-tuning is NOT feasible in this environment (grounds in
extraction/interface.py) and no training pipeline exists.

Cases: 11 synthetic patterns · TP=15 FP=0 FN=0

| Precision | Recall | F1 |
|---|---|---|
| 1.000 | 1.000 | 1.000 |

## Per-case detail
* `The accused is charged under Section 379 IPC for theft of a ` — gold ["('IPC_1860', '379')"] / extracted ["('IPC_1860', '379')"]
* `Chargesheet filed under s. 303(2) BNS and Section 316 BNS.` — gold ["('BNS_2023', '303(2)')", "('BNS_2023', '316')"] / extracted ["('BNS_2023', '303(2)')", "('BNS_2023', '316')"]
* `Offence under section 20 NDPS Act, intermediate quantity all` — gold ["('NDPS_1985', '20')"] / extracted ["('NDPS_1985', '20')"]
* `FIR under Section 420 of the Indian Penal Code for cheating.` — gold ["('IPC_1860', '420')"] / extracted ["('IPC_1860', '420')"]
* `Booked under sec 304A IPC; causing death by negligence.` — gold ["('IPC_1860', '304A')"] / extracted ["('IPC_1860', '304A')"]
* `Complaint registered under section 154 CrPC; no charge yet.` — gold ["(None, '154')"] / extracted ["(None, '154')"]
* `Charged with murder under Section 103(1) BNS.` — gold ["('BNS_2023', '103(1)')"] / extracted ["('BNS_2023', '103(1)')"]
* `Sections 341 and 351 IPC invoked for wrongful restraint and ` — gold ["('IPC_1860', '341')", "('IPC_1860', '351')"] / extracted ["('IPC_1860', '341')", "('IPC_1860', '351')"]
* `Accused booked u/s 379, 411 and 420 IPC after recovery.` — gold ["('IPC_1860', '379')", "('IPC_1860', '411')", "('IPC_1860', '420')"] / extracted ["('IPC_1860', '379')", "('IPC_1860', '411')", "('IPC_1860', '420')"]
* `The seizure was of 12 grams; no section is cited in this par` — gold [] / extracted []
* `Charge under s.111 BNS (organised crime) with s. 61(2) BNS c` — gold ["('BNS_2023', '111')", "('BNS_2023', '61(2)')"] / extracted ["('BNS_2023', '111')", "('BNS_2023', '61(2)')"]
