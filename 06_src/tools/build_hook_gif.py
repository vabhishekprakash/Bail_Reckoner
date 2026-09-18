"""Build the README hook GIF: a terminal walk through the six gates (05_docs/assets/hook.gif).

Run:  cd 06_src && ./.venv/Scripts/python.exe tools/build_hook_gif.py

Round 24 produced the first GIF without keeping the script, so the only way to change a word
in it was to redraw the whole thing by hand. This module is that script, reconstructed from
the original's own pixels: 880x430, Consolas 19 in regular and bold, a 27-pixel row grid with
the first baseline at y=26, text at x=28 or indented to x=48, and the three colours below.
Frames 0 to 13 of the original reproduce from it byte for byte (tools/../.cache checks this
during development), so a future edit changes only what it means to change.

Two rules this file exists to keep:

* **The closing card states no row count.** The first version ended on "Verified statutory
  rows in the database: 0", which went stale the moment a reviewer signed the first five and
  left the image contradicting the README section beneath it. The card now says where the
  count comes from (every response states it) rather than what it is.
* **The walk is SYNTHETIC and says so.** Section 901 is a fixture, not a statute, and the
  command line carries `--mode synthetic`. Nothing here may show a real offence's maximum:
  that would put an unverified-looking number in the most-read image of the project.

The GIF is a committed binary artefact, so regenerating it deliberately (and committing the
result) is the whole workflow; nothing builds it automatically.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = (880, 430)
BG = (16, 18, 20)
BRIGHT = (222, 224, 226)
GREY = (140, 144, 148)

ROW_ZERO_Y = 26
ROW_HEIGHT = 27
X_MARGIN = 28
X_INDENT = 48
X_IDLE_CURSOR = 34
CURSOR_SIZE = (11, 20)

FONT_DIR = Path(r"C:\Windows\Fonts")
REGULAR_FILE = FONT_DIR / "consola.ttf"
BOLD_FILE = FONT_DIR / "consolab.ttf"
FONT_SIZE = 19

OUTPUT = Path(__file__).resolve().parents[2] / "05_docs" / "assets" / "hook.gif"

Line = tuple[int, int, str, bool, tuple[int, int, int]]
"""(row, x, text, bold, colour)."""

PROMPT = '$ bail-reckoner --case "FIR 201/2022" --mode synthetic'

WALK: list[Line] = [
    (0, X_MARGIN, PROMPT, True, BRIGHT),
    (2, X_INDENT, "offence   s.901 (synthetic) . max sentence 7 years", False, GREY),
    (3, X_INDENT, "custody   arrest 2022-06-01 . 1,523 days as on 2026-08-01", False, GREY),
    (5, X_INDENT, "GATE 0  custody vs absolute cap ........ within the maximum", False, BRIGHT),
    (6, X_INDENT, "GATE 1  death or life prescribed? ...... no", False, BRIGHT),
    (7, X_INDENT, "GATE 2  multiple cases pending? ........ no", False, BRIGHT),
    (8, X_INDENT, "GATE 3  special-statute restriction? ... none in scope", False, BRIGHT),
    (9, X_INDENT, "GATE 4  first-time offender? ........... no -> one-half applies", False, BRIGHT),
    (10, X_INDENT, "GATE 5  threshold 42 months ............ crossed on 2025-12-01", False, BRIGHT),
    (12, X_INDENT, "Statutory entitlement to release identified.", True, BRIGHT),
    (
        13,
        X_INDENT,
        "Every step above cites s.479, BNSS 2023. Working shown in full.",
        False,
        GREY,
    ),
]

CARD: list[Line] = [
    (3, X_MARGIN, "SYNTHETIC DEMONSTRATION", True, BRIGHT),
    (
        5,
        X_MARGIN,
        "Offences outside the verified database abstain rather than guess.",
        False,
        BRIGHT,
    ),
    (6, X_MARGIN, "Every response states how many verified rows exist.", False, BRIGHT),
    (8, X_MARGIN, "A calculator with citations. Never a decision-maker.", False, GREY),
]

# (lines shown, cursor row, cursor after that line's text or None for an idle cursor, ms).
Step = tuple[int, int, bool, int]
STEPS: list[Step] = [
    (1, 0, True, 350),
    (1, 1, False, 350),
    (2, 2, True, 350),
    (3, 3, True, 350),
    (3, 4, False, 350),
    (4, 5, True, 650),
    (5, 6, True, 650),
    (6, 7, True, 650),
    (7, 8, True, 650),
    (8, 9, True, 650),
    (9, 10, True, 650),
    (9, 11, False, 350),
    (10, 12, True, 350),
    (11, 13, True, 2400),
]
CARD_MS = 4200


def _fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    missing = [f for f in (REGULAR_FILE, BOLD_FILE) if not f.is_file()]
    if missing:
        raise SystemExit(
            f"cannot build the hook GIF: {', '.join(str(m) for m in missing)} not found. "
            f"The image is drawn in Consolas; substituting another font would change every "
            f"glyph in the most-read image in the README, so this stops rather than guesses."
        )
    return (
        ImageFont.truetype(str(REGULAR_FILE), FONT_SIZE),
        ImageFont.truetype(str(BOLD_FILE), FONT_SIZE),
    )


def _render(lines: list[Line], cursor: tuple[int, int] | None) -> Image.Image:
    regular, bold = _fonts()
    canvas = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(canvas)
    for row, x, text, is_bold, colour in lines:
        draw.text((x, ROW_ZERO_Y + row * ROW_HEIGHT), text, font=bold if is_bold else regular,
                  fill=colour)
    if cursor is not None:
        x, row = cursor
        top = ROW_ZERO_Y + row * ROW_HEIGHT
        draw.rectangle((x, top, x + CURSOR_SIZE[0] - 1, top + CURSOR_SIZE[1] - 1), fill=BRIGHT)
    return canvas


def _cursor_x(line: Line) -> int:
    """Six pixels past the last glyph's ink box, which is where the original sits.

    Measured, not chosen: the advance width of the final character would put the block a
    little further right, and the difference is visible when the two GIFs are flicked
    between.
    """
    regular, bold = _fonts()
    row, x, text, is_bold, _ = line
    scratch = ImageDraw.Draw(Image.new("RGB", SIZE, BG))
    right = scratch.textbbox(
        (x, ROW_ZERO_Y + row * ROW_HEIGHT), text, font=bold if is_bold else regular
    )[2]
    return right + 6


def build() -> Path:
    frames: list[Image.Image] = []
    durations: list[int] = []
    for shown, cursor_row, after_text, milliseconds in STEPS:
        lines = WALK[:shown]
        if after_text:
            cursor = (_cursor_x(lines[-1]), cursor_row)
        else:
            cursor = (X_IDLE_CURSOR, cursor_row)
        frames.append(_render(lines, cursor))
        durations.append(milliseconds)
    frames.append(_render(CARD, None))
    durations.append(CARD_MS)

    palette = frames[0].quantize(colors=32)
    quantized = [frame.quantize(palette=palette) for frame in frames]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(
        OUTPUT,
        save_all=True,
        append_images=quantized[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {path} ({path.stat().st_size:,} bytes, {len(STEPS) + 1} frames)")
