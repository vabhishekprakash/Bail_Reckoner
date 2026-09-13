"""Tests for the REST API (D-076): the contract, the honesty layer, and the audit chain.

Fixtures are synthetic and labelled as such; no real accused person's data appears here.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from bail_reckoner.api import create_app
from bail_reckoner.audit import AuditLog

SYNTHETIC_REQUEST: dict[str, Any] = {
    "date_of_arrest": "2022-06-01",
    "evaluated_on": "2026-08-01",
    "cases": [
        {
            "case_ref": "FIR 201/2022, PS Test-Town",
            "offences": [
                {
                    "regime": "BNS_2023",
                    "section": "901",
                    "label": "Synthetic offence A",
                }
            ],
        }
    ],
    "prior_conviction_status": "KNOWN_PRIOR",
    "case_list_verified": True,
    "mode": "synthetic",
}


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    base = tmp_path_factory.mktemp("api")
    app = create_app(repository_path=base / "penalty.sqlite3", audit_path=base / "audit.jsonl")
    return TestClient(app)


class TestMeta:
    def test_meta_names_zero_rows_and_both_full_verdicts(self, client: TestClient) -> None:
        body = client.get("/v1/meta").json()
        assert body["verified_row_count"] == 0
        assert "ZERO VERIFIED PENALTY ROWS EXIST" in body["data_warning"]
        assert "Statutory sources on record" in body["sources_line"]
        # D-010's two verdicts, in full — the contract exposes no shorthand.
        assert body["verdict_values"] == [
            "ENTITLEMENT_ESTABLISHED",
            "NO_ENTITLEMENT_IDENTIFIED — HUMAN REVIEW REQUIRED",
        ]


class TestHonestyLayer:
    def test_verified_mode_with_zero_rows_abstains_and_warns(self, client: TestClient) -> None:
        """D-060 at the boundary: no caller-supplied maximum exists, the empty verified
        database resolves nothing, so the computation abstains — and says so unmissably."""
        request = dict(SYNTHETIC_REQUEST, mode="verified")
        body = client.post("/v1/reports", json=request).json()
        assert "ZERO VERIFIED PENALTY ROWS EXIST" in body["data_warning"]
        flat = " ".join(body["rendered_text"].split())
        assert "no verified maximum sentence is available" in flat or "no threshold" in flat
        assert "No statutory entitlement identified" in body["report"]["status_text"]

    def test_synthetic_mode_computes_and_warns(self, client: TestClient) -> None:
        body = client.post("/v1/reports", json=SYNTHETIC_REQUEST).json()
        assert body["mode"] == "synthetic"
        assert "SYNTHETIC FIXTURES IN USE" in body["data_warning"]
        # The fixture 3-year offence with ~50 months custody: entitlement established.
        assert body["report"]["status_text"].startswith("Statutory entitlement to release")

    def test_report_carries_the_full_verdict_sentence(self, client: TestClient) -> None:
        body = client.post("/v1/reports", json=SYNTHETIC_REQUEST).json()
        # Full sentence prose, never "Eligible" (D-077 constraint 2).
        assert "Eligible" not in body["rendered_text"]
        assert (
            "Statutory entitlement to release under Section 479(1), BNSS 2023 is "
            "established on the inputs provided." in " ".join(body["rendered_text"].split())
        )

    def test_uniformity_and_sources_lines_travel_with_the_maximum(self, client: TestClient) -> None:
        body = client.post("/v1/reports", json=SYNTHETIC_REQUEST).json()
        flat = " ".join(body["rendered_text"].split())
        assert "assume national uniformity" in flat
        assert "Statutory sources on record" in flat


class TestApplications:
    def test_refusal_is_http_200_with_every_reason(self, client: TestClient) -> None:
        request = dict(SYNTHETIC_REQUEST, case_list_verified=False)
        response = client.post("/v1/applications", json=request)
        assert response.status_code == 200
        body = response.json()
        assert body["kind"] == "refusal"
        conditions = {r["condition"] for r in body["refusal_reasons"]}
        assert "case_list_unverified" in conditions

    def test_generated_application_round_trips(self, client: TestClient) -> None:
        body = client.post("/v1/applications", json=SYNTHETIC_REQUEST).json()
        assert body["kind"] == "application"
        flat = " ".join(body["rendered_text"].split())
        assert "APPLICATION UNDER SECTION 479(3)" in flat
        assert "SYNTHETIC FIXTURES IN USE" in body["data_warning"]

    def test_pdf_endpoint_returns_deterministic_pdf(self, client: TestClient) -> None:
        first = client.post("/v1/applications/pdf", json=SYNTHETIC_REQUEST)
        second = client.post("/v1/applications/pdf", json=SYNTHETIC_REQUEST)
        assert first.status_code == 200
        assert first.headers["content-type"] == "application/pdf"
        assert first.content == second.content
        reader = PdfReader(io.BytesIO(first.content))
        assert "APPLICATION UNDER SECTION 479(3)" in reader.pages[0].extract_text()

    def test_pdf_endpoint_refusal_matches_the_applications_endpoint(
        self, client: TestClient
    ) -> None:
        """A refusal is a computed outcome on both endpoints: same status, same body shape;
        content type distinguishes a document from a refusal."""
        request = dict(SYNTHETIC_REQUEST, case_list_verified=False)
        pdf_route = client.post("/v1/applications/pdf", json=request)
        json_route = client.post("/v1/applications", json=request)
        assert pdf_route.status_code == json_route.status_code == 200
        assert pdf_route.headers["content-type"].startswith("application/json")
        assert pdf_route.json() == json_route.json()


class TestBoundary:
    def test_no_user_supplied_maximum_is_accepted(self, client: TestClient) -> None:
        """D-060: a maximum in the request must be rejected as an unknown field, not
        silently dropped — silently dropping it would let a caller believe it was used."""
        request = dict(SYNTHETIC_REQUEST)
        request["cases"] = [
            {
                "case_ref": "FIR 1/2022",
                "offences": [
                    {
                        "regime": "BNS_2023",
                        "section": "902",
                        "label": "x",
                        "maximum_months": 84,
                    }
                ],
            }
        ]
        response = client.post("/v1/reports", json=request)
        assert response.status_code == 422

    def test_verification_affirmations_default_to_false(self, client: TestClient) -> None:
        request = {k: v for k, v in SYNTHETIC_REQUEST.items() if k != "case_list_verified"}
        body = client.post("/v1/applications", json=request).json()
        assert body["kind"] == "refusal"  # unverified list blocks the filing by default


class TestAuditLog:
    def test_every_computation_appends_and_the_chain_verifies(self, tmp_path: Path) -> None:
        audit_path = tmp_path / "audit.jsonl"
        app = create_app(repository_path=tmp_path / "penalty.sqlite3", audit_path=audit_path)
        local = TestClient(app)
        local.post("/v1/reports", json=SYNTHETIC_REQUEST)
        local.post("/v1/applications", json=SYNTHETIC_REQUEST)
        lines = [ln for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln]
        assert len(lines) == 2
        assert AuditLog(audit_path).verify_chain()

    def test_tampering_breaks_the_chain(self, tmp_path: Path) -> None:
        audit_path = tmp_path / "audit.jsonl"
        log = AuditLog(audit_path)
        log.append({"endpoint": "reports", "inputs_hash": "a"})
        log.append({"endpoint": "reports", "inputs_hash": "b"})
        tampered = audit_path.read_text(encoding="utf-8").replace(
            '"inputs_hash": "a"', '"inputs_hash": "z"'
        )
        audit_path.write_text(tampered, encoding="utf-8")
        assert not AuditLog(audit_path).verify_chain()

    def test_truncation_from_the_end_breaks_verification(self, tmp_path: Path) -> None:
        """A hash chain alone cannot see deletion from the end — the survivors stay
        contiguous. The head-state sidecar (count + head hash) is what catches it."""
        audit_path = tmp_path / "audit.jsonl"
        log = AuditLog(audit_path)
        for i in range(3):
            log.append({"endpoint": "reports", "inputs_hash": str(i)})
        assert log.verify_chain()
        lines = audit_path.read_text(encoding="utf-8").splitlines()
        audit_path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
        assert not AuditLog(audit_path).verify_chain()

    def test_module_has_no_update_or_delete_path(self) -> None:
        public = [n for n in dir(AuditLog) if not n.startswith("_")]
        assert sorted(public) == ["append", "verify_chain"]


class TestDemonstratorPage:
    """D-077's hard UI constraints, asserted on the served page itself."""

    @pytest.fixture(scope="class")
    @staticmethod
    def page(client: TestClient) -> str:
        response = client.get("/")
        assert response.status_code == 200
        return response.text

    def test_affirmations_are_never_pre_ticked(self, page: str) -> None:
        # No checkbox on the page carries a checked attribute, and each states what is
        # being affirmed at the point of affirmation.
        assert "checked>" not in page and "checked " not in page.replace(".checked", "")
        assert "I affirm that the prior-conviction status" in page
        assert "I affirm that the case listed above is the only" in page

    def test_no_shorthand_verdict_vocabulary(self, page: str) -> None:
        assert "Eligible" not in page
        assert "Not eligible" not in page

    def test_no_maximum_input_exists(self, page: str) -> None:
        """D-060 in the form: the maximum is stated to be resolved, never entered."""
        assert "maximum sentence is never entered here" in page
        assert 'name="maximum' not in page

    def test_stack_ruling_is_stated_on_the_page(self, page: str) -> None:
        """Formerly asserted the D-058 conflict was open; the assertion moves with the
        ruling (D-084, 2026-08-26): the page now states server-first and the recorded
        EA divergence."""
        assert "D-084" in page
        assert "server-rendered interface" in page

    def test_i18n_chrome_mechanism_with_empty_unreviewed_slots(self, page: str) -> None:
        """D-090 option (b): the language mechanism exists, English is complete, and the
        hi/te dictionaries are EMPTY awaiting a human-reviewed translation. No Devanagari
        or Telugu glyph may appear anywhere in the page — a single machine-translated
        string here would be unreviewed legal-adjacent language shipped to the
        least-equipped readers (council-reviewed, unanimous)."""
        assert '<option value="hi">Hindi</option>' in page
        assert '<option value="te">Telugu</option>' in page
        assert "awaiting a human-reviewed translation" in page
        assert "awaits a human-reviewed translation" in page
        assert "English-only in every language setting" in page
        assert not any("ऀ" <= ch <= "ॿ" for ch in page), "Devanagari found"
        assert not any("ఀ" <= ch <= "౿" for ch in page), "Telugu script found"

    def test_no_disclosure_toggles_around_output(self, page: str) -> None:
        assert "<details" not in page
        assert "nothing is summarised away" in page

    def test_no_status_iconography(self, page: str) -> None:
        """No tick/cross/badge glyphs anywhere in the page source (D-035, D-068 §4)."""
        for glyph in ("✓", "✔", "✗", "✘", "⚠"):
            assert glyph not in page


class TestUrgentChrome:
    """Item 3 (Abhishek, 2026-08-19): the urgent flag renders as page chrome above the
    pane, since narrow viewports pan the pane horizontally and nothing safety-critical may
    hide behind a horizontal scroll."""

    def test_report_payload_carries_the_urgent_notice_for_the_chrome(
        self, client: TestClient
    ) -> None:
        """The API side: an over-cap case's serialized report exposes urgent_notice, which
        is what the page restates as chrome."""
        request = dict(SYNTHETIC_REQUEST)
        # Fixture s.905 is the 6-month synthetic offence; custody since 2022 is far past it.
        request["cases"] = [
            {
                "case_ref": "FIR 7/2024, PS Gamma",
                "offences": [
                    {"regime": "BNS_2023", "section": "905", "label": "Synthetic offence E"}
                ],
            }
        ]
        body = client.post("/v1/reports", json=request).json()
        notice = body["report"]["urgent_notice"]
        assert notice is not None
        assert notice["heading"] == "MOST URGENT — READ FIRST"
        assert "custody undergone has reached the maximum" in notice["body"]

    def test_page_restates_the_urgent_notice_outside_the_pane(self, client: TestClient) -> None:
        """The page side, pinned at source level (no browser in this environment): the
        script renders urgent_notice as chrome above the document frame, and says why."""
        page = client.get("/").text
        assert "urgent_notice" in page
        assert "ABOVE the pane" in page
        assert "restatement of ONE flag outside the artefact" in page
        # The chrome block precedes the document frame in the constructed markup: the
        # render function concatenates `urgent` first. (Source-level pin — no browser
        # exists in this environment to assert on a live DOM.)
        fn = page[page.index("function showDocument") :]
        assert fn.index("urgent +") < fn.index("document-frame")


class TestOfflineReadiness:
    def test_no_cdn_or_external_resource_in_the_page(self, client: TestClient) -> None:
        """Offline and intermittently connected terminals are a named deployment target:
        the page must load with zero network access beyond the API itself."""
        page = client.get("/").text
        for marker in ("fonts.googleapis", "fonts.gstatic", "cdn.", "https://", "http://"):
            in_markup = [
                line
                for line in page.splitlines()
                if marker in line and "docs.pytest" not in line and not line.strip().startswith("*")
            ]
            # https:// may appear only inside comments explaining the rule, never in a
            # link/src/import that the browser would fetch.
            for line in in_markup:
                assert "import" not in line and "src=" not in line and "href=" not in line, line


class TestExtractionEndpointAndConfirmationPanel:
    """Layer B over HTTP + the D-077-constrained confirmation view (round 17)."""

    def test_extract_returns_candidates_with_unresolved_displayed(self, client: TestClient) -> None:
        body = client.post(
            "/v1/extract",
            json={"text": "Charged u/s 379 IPC; complaint under section 154 CrPC."},
        ).json()
        assert body["kind"] == "extraction"
        assert body["model_involved"] is False
        keyed = {(c["regime"], c["section"], c["unresolved"]) for c in body["candidates"]}
        assert ("IPC_1860", "379", False) in keyed
        # The refusal is IN the payload, flagged — never omitted (fourth-instance rule).
        assert (None, "154", True) in keyed
        assert "unresolved candidates are displayed, never omitted" in body["data_note"].lower()

    def test_extract_never_logs_the_text(self, tmp_path: Path) -> None:
        """DPDP: the audit records length and hash, never content."""
        audit_path = tmp_path / "audit.jsonl"
        app = create_app(repository_path=tmp_path / "p.sqlite3", audit_path=audit_path)
        local = TestClient(app)
        marker = "SYNTHETIC-MARKER-THAT-MUST-NOT-PERSIST u/s 379 IPC"
        local.post("/v1/extract", json={"text": marker})
        logged = audit_path.read_text(encoding="utf-8")
        assert "SYNTHETIC-MARKER" not in logged
        assert "text_sha256" in logged

    def test_panel_shows_refusals_and_requires_named_confirmer(self, client: TestClient) -> None:
        page = client.get("/").text
        assert "displayed, never omitted" in page
        assert "the enactment is not named in the text" in page
        assert "Confirmation requires a named person. It is never automatic." in page
        assert "choose the enactment" in page
        # D-077 holds: no pre-ticked affirmation appeared with the panel.
        assert "checked>" not in page


class TestEngineRefusalTranslation:
    """D-092: an engine refusal reaches the caller as a 422 carrying its reason, never a
    reason-less 500 — the API must not misrepresent a deliberate refusal as a crash."""

    def test_contradictory_exclusion_returns_422_with_the_reason(
        self, client: TestClient
    ) -> None:
        payload = dict(SYNTHETIC_REQUEST, excluded_days=100000)
        response = client.post("/v1/reports", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert "contradict" in body["engine_refusal"]
        assert "refusal, not a crash" in body["note"]

    def test_evaluated_before_arrest_is_a_worded_refusal_too(
        self, client: TestClient
    ) -> None:
        payload = dict(SYNTHETIC_REQUEST, evaluated_on="2020-01-01")
        response = client.post("/v1/reports", json=payload)
        assert response.status_code == 422
        assert "precedes" in response.json()["engine_refusal"]
