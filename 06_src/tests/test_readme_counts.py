"""The README's test count cannot drift from the suite.

The count in the README is a claim about this repository, and it went stale three times in
three rounds: the loader added 23 tests, the export guard added 3, the mandatory-minimum work
added 6, and each time the number on the page was corrected by hand afterwards. A figure that
is only ever checked by remembering to check it is a figure that will be wrong again, so the
suite checks it.

Scope, deliberately narrow: this pins the collected total, the one number a reader can verify
by running `pytest -q`. The pass/skip split and the fresh-clone figures in the same section
depend on what is built in the checkout (the corpus, the runtime audit log), so no test can
assert them without asserting the state of the machine it runs on; they are measured by hand
and stated with the conditions attached.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

README_PATH = Path(__file__).resolve().parents[2] / "README.md"
_TOTAL = re.compile(r"(\d[\d,]*) automated tests")


def test_the_readme_total_matches_the_collected_count(request: pytest.FixtureRequest) -> None:
    if request.config.option.file_or_dir:
        pytest.skip(
            "partial run: the README figure is a whole-suite total, and a subset would "
            "compare it against a handful of tests — a visible skip, not a silent pass"
        )
    assert README_PATH.is_file(), README_PATH
    match = _TOTAL.search(README_PATH.read_text(encoding="utf-8"))
    assert match is not None, (
        f"{README_PATH} states no test total: the honest-status section must say "
        f"'N automated tests', because that sentence is what this test keeps true"
    )
    stated = int(match.group(1).replace(",", ""))
    collected = request.session.testscollected
    assert stated == collected, (
        f"{README_PATH} says {stated} automated tests; this suite collects {collected}. "
        f"Update the README in the commit that changed the count."
    )
