"""Layer C — the deterministic entitlement engine. The defensible core of the project.

Purity contract (CLAUDE.md section 6, D-050): no network, no model, no file or database I/O
inside the decision path. Deterministic functions over typed, frozen inputs, using only the
standard library. Penalty data is passed in, never fetched here.

Gate order is fixed (CLAUDE.md section 3, as amended by D-033/D-034). Six gates:

    0  Custody >= maximum prescribed?      ALWAYS FIRST -> DETAINED_BEYOND_MAXIMUM, highest
                                           severity, never masked by a later gate.
                                           s.479(1) third proviso.
    1  Death or life imprisonment?         BAR. s.479(1) main clause.
    2  Multiple offences / multiple cases?  BAR, scope configurable, default NARROW (D-025).
                                           s.479(2).
    3  Special-statute bail bar?            FLAG, never terminal (D-033).
                                           SPECIAL_STATUTE_TEST_REQUIRED.
    4  First-time offender?                 SELECTS THE FRACTION, 1/3 on bond vs 1/2 on bail.
                                           Not a bar. s.479(1) first proviso.
    5  Custody >= applicable threshold?     TEST. s.479(1).

There is no INELIGIBLE state anywhere in this package (D-010). The verdict is binary --
ENTITLEMENT_ESTABLISHED or NO_ENTITLEMENT_IDENTIFIED -- and everything else is a typed flag
(D-048). A false "eligible" is caught by the court; a false "ineligible" silently keeps a person
in custody and nobody appeals a machine's silence.

Discretionary factors are never scored (D-009): flight risk and witness influence are echoed back
as an unweighted list for a human, with no weights, no composite and no ranking.
"""
