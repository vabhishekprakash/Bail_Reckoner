"""PDF renderer for the s.479(3) application (D-073).

Renders the same `Application` object as the text renderer — in fact it renders the text
renderer's exact output, paginated in a monospaced face, so the two artefacts can never say
different things: the byte-comparable text rendering remains the single source of truth and
the regression artefact, and the PDF is its paper form.

**Stdlib-only, deliberately (D-073).** pyproject's rule is that every dependency is a C4
decision pinned on approval, and none exists for a PDF library. A filing is a fixed-layout
monospaced document; a full PDF engine buys nothing for it, and a minimal writer keeps every
byte of a court-document path auditable in this repository. The writer emits PDF 1.4 with a
built-in Courier font (WinAnsi encoding), no /CreationDate, no /ID and no compression — the
same `Application` always produces the same bytes. Abhishek's rule stands regardless: a PDF
is never the regression artefact; tests assert on extracted text and determinism, not on a
stored PDF golden.

A character outside WinAnsi (cp1252) raises rather than substitutes: a silently replaced
character in a court filing is a convenience default on legal text (D-064).
"""

from __future__ import annotations

from bail_reckoner.reporting.application import Application
from bail_reckoner.reporting.render_application_text import render_application_text

__all__ = ["render_application_pdf"]

# A4, points.
_PAGE_W = 595
_PAGE_H = 842
_MARGIN_X = 57  # ~20 mm
_MARGIN_TOP = 57
_MARGIN_BOTTOM = 57
_FONT_SIZE = 8.5
_LEADING = 10.5

_LINES_PER_PAGE = int((_PAGE_H - _MARGIN_TOP - _MARGIN_BOTTOM) / _LEADING)


class PdfEncodingError(ValueError):
    """A character in the filing cannot be represented in the PDF's WinAnsi encoding."""


def _pdf_text(line: str) -> bytes:
    r"""Encode one line for a PDF literal string: cp1252, with ( ) \ escaped."""
    try:
        raw = line.encode("cp1252")
    except UnicodeEncodeError as exc:
        raise PdfEncodingError(
            f"character {line[exc.start]!r} in {line!r} has no WinAnsi encoding; "
            f"refusing to substitute (D-064)"
        ) from exc
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _content_stream(lines: list[str]) -> bytes:
    parts = [
        b"BT\n/F1 %s Tf\n%d %d Td\n%s TL\n"
        % (
            str(_FONT_SIZE).encode("ascii"),
            _MARGIN_X,
            _PAGE_H - _MARGIN_TOP,
            str(_LEADING).encode("ascii"),
        )
    ]
    for line in lines:
        parts.append(b"(" + _pdf_text(line) + b") Tj T*\n")
    parts.append(b"ET\n")
    return b"".join(parts)


def render_application_pdf(application: Application) -> bytes:
    """Render the application draft to PDF bytes. Deterministic: same object, same bytes."""
    text = render_application_text(application)
    all_lines = text.split("\n")
    pages = [all_lines[i : i + _LINES_PER_PAGE] for i in range(0, len(all_lines), _LINES_PER_PAGE)]
    # A trailing empty chunk from the final newline renders as a blank page; drop it.
    pages = [p for p in pages if any(line.strip() for line in p)] or [[""]]

    # Object numbering: 1 catalog, 2 pages, 3 font, then per page: page object + content.
    objects: list[bytes] = []

    def obj(number: int, body: bytes) -> bytes:
        return b"%d 0 obj\n%s\nendobj\n" % (number, body)

    first_page_obj = 4
    page_refs = b" ".join(b"%d 0 R" % (first_page_obj + 2 * i) for i in range(len(pages)))
    objects.append(obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    objects.append(obj(2, b"<< /Type /Pages /Kids [" + page_refs + b"] /Count %d >>" % len(pages)))
    objects.append(
        obj(
            3,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>",
        )
    )
    for i, page_lines in enumerate(pages):
        page_num = first_page_obj + 2 * i
        content_num = page_num + 1
        objects.append(
            obj(
                page_num,
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
                b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>"
                % (_PAGE_W, _PAGE_H, content_num),
            )
        )
        stream = _content_stream(page_lines)
        objects.append(
            obj(
                content_num,
                b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
            )
        )

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    out = bytearray(header)
    offsets: list[int] = []
    for body in objects:
        offsets.append(len(out))
        out.extend(body)

    xref_at = len(out)
    count = len(objects) + 1
    out.extend(b"xref\n0 %d\n" % count)
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        out.extend(b"%010d 00000 n \n" % offset)
    # No /ID and no /Info: both are where nondeterminism (file hashes, timestamps) enters.
    out.extend(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (count, xref_at))
    return bytes(out)
