"""Section-wise eligibility report and the s.479(3) Superintendent's application generator.

Report shape is fixed (CLAUDE.md section 6):
    offence -> section -> max sentence -> custody -> fraction served -> s.479 threshold -> status

Rules that govern every report:

* The working is always shown, including when a bar fires (D-035). The verdict is controlled
  solely by the fired gate, and a barred report carries no success styling -- no "CROSSED", no
  green, no affirmation of any kind.
* Deck slide 12 is a pre-D-025 mockup and is explicitly NOT the template. Derive the template
  from the CLAUDE.md section 6 field list. The mockup also paraphrases s.479(2) where verbatim
  quotation is required.
* Provisions are quoted verbatim from `01_law/Section_479_BNSS_2023.md`. Never paraphrase a
  provision into a report, and never quote statute from memory (C5).
* The second proviso appears as a standing note quoting the proviso, never as a gate (D-040).
* Every report carries an empty `Legally reviewed by: ______________` field that stays empty
  until a human signs it, and every output is stamped with statute_version, law_in_force_on,
  inputs_hash, timestamp, rules_fired[] and reviewed_by.
"""

from bail_reckoner.reporting.application import (
    Application,
    ApplicationLanguage,
    ApplicationLanguageError,
    ApplicationRefusal,
    build_application,
    load_application_language,
)
from bail_reckoner.reporting.language import (
    ReportLanguage,
    ReportLanguageError,
    load_report_language,
)
from bail_reckoner.reporting.render_application_pdf import render_application_pdf
from bail_reckoner.reporting.render_application_text import render_application_text
from bail_reckoner.reporting.render_text import render_text
from bail_reckoner.reporting.report import Report, build_report

__all__ = [
    "Application",
    "ApplicationLanguage",
    "ApplicationLanguageError",
    "ApplicationRefusal",
    "build_application",
    "load_application_language",
    "render_application_pdf",
    "render_application_text",
    "ReportLanguage",
    "ReportLanguageError",
    "load_report_language",
    "Report",
    "build_report",
    "render_text",
]
