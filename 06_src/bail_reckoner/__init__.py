"""Bail Reckoner — statutory entitlement to release under Section 479 BNSS 2023 (Act 46 of 2023).

Computes what the statute already provides, shows the arithmetic, and cites the provision behind
every step. Decision-support for legal-aid providers, Undertrial Review Committees and jail
authorities — never an autonomous decision-maker, and never a predictor of bail outcomes (D-012).

Layer map:
    engine      Layer C — deterministic six-gate entitlement engine. Pure: no network, no model,
                no I/O in the decision path (D-050: stdlib only).
    statutes    Offence -> maximum-sentence lookup and statute versioning.
    retrieval   Layer A — statutory corpus retrieval.
    extraction  Layer B — charge-sheet parsing. Extracts; never decides.
    precedent   Layer D — precedent retrieval, verbatim extracts only.
    reporting   Section-wise report and the s.479(3) Superintendent's application.
    audit       Append-only audit log. No update path, no delete path.
    api         FastAPI service layer.

The canonical text of s.479 is `01_law/Section_479_BNSS_2023.md`, verified against the Gazette of
India (Extraordinary, Part II-Sec. 1, No. 54, 25 December 2023, p. 144) on 2026-08-12. Quote the
provision from that file; never from memory.
"""

__version__ = "0.0.1"
