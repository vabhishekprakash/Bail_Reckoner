"""Layer B — charge-sheet parsing and section extraction. Extracts; never decides.

The model's output is a candidate set of offences and sections handed to Layer C. No extraction
result is ever a verdict, and nothing in this package may short-circuit a gate.

Input scope at MVP is structured form fields (D-026); this widens to typed or digital
charge-sheet text at M5. OCR and scanned-document handling are out of scope and are recorded as a
stated limitation, not hidden. Input parsing stays English (D-030) -- multilingual is UI-only and
deferred to M7.

Data policy (D-038), which binds from today even though the pipeline lands at M5: judgment-derived
material may be used for extraction training and evaluation in redacted form only, stored under
`02_data/` which is gitignored and never committed. Raw unredacted downloads never enter the
repository in any form. Nothing judgment-derived ever enters `03_goldenset/` -- fixtures there are
synthetic and labelled as such in the file header. No real accused person's data is committed,
ever.
"""
