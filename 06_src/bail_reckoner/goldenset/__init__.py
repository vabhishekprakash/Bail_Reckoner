"""M3 golden-set harness (D-065, council-reviewed).

Loads labelled cases from `03_goldenset/`, runs them through the six-gate engine, and scores
three headline columns per case: verdict, fired gate, day-exact qualifying date. Everything else
this package does exists to keep that number honest:

* **Labels never embed a maximum sentence.** A case references an offence by
  (regime, section, variant); the maximum comes from the same rows the engine reads. A label
  with a maximum inside it is a second copy of the law, and two copies drift.
* **Expected values are hand-computed and version-pinned.** When the penalty source changes,
  affected cases fail loudly as STALE — a third result class, never a silent pass or fail — and
  are re-derived by hand. The harness never recomputes expected values through the engine's own
  arithmetic; that would test the engine against itself.
* **CONTESTED scores as abstention**, its own reported row, never inside an accuracy figure —
  with guards in both directions: a confident answer on a CONTESTED-labelled case is a failure,
  and an expected DETAINED_BEYOND_MAXIMUM flag missing from the output is a failure regardless
  of any contested routing.
* **Tier discipline (CLAUDE.md §7):** Tier-1 and Tier-2 results are reported separately and
  never blended. The Tier-1 number is claimable only as *"correct under the recorded arithmetic
  conventions (OLQ-9/OLQ-10), which are themselves unverified design choices"*.
* **D-010 at load time:** a case whose expected verdict is anything but the two permitted states
  is refused before anything runs.

Fixture rows for smoke runs are SYNTHETIC and say so in their file header; nothing in
`03_goldenset/` is or may become judgment-derived (D-038).
"""
