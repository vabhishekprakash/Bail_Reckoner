# Bail Reckoner — UI design specification (D-077)

**Prepared 19 August 2026** using the `ui-ux-pro-max` design-intelligence skill and the
`frontend-design` plugin, on Abhishek's explicit direction. This spec binds any frontend
built on the API, whichever stack D-058's open call lands on. The served page at `/` is an
**API-contract demonstrator**, not the committed frontend.

## Identity

A **government form and its filed document** — not a SaaS application. The user is a
legal-aid paralegal, UTRC member or jail clerk on a district-office machine. The page's
single job: enter case facts, receive the computation document.

**Signature element (and the true fact it encodes):** the report pane renders the canonical
fixed-layout text artefact **byte-for-byte, in monospace, framed like a filed page**. The UI
never re-typesets the computation, so the UI can never say something the regression artefact
does not. The frame is the design; the document is the content.

## Tokens

| Token | Value | Role |
|---|---|---|
| `--paper` | `#FAFAF7` | page background — paper, not screen-white |
| `--ink` | `#161A1D` | text, rules, borders, the warning box |
| `--muted` | `#5A6167` | captions and hints |
| `--rule` | `#C9CCCE` | hairline separators, the frame's offset shadow |
| `--interactive` | `#1D4ED8` | links, buttons, focus rings — **interactive affordance only, never status** |

Type: system stacks only in the demonstrator (Georgia serif for headings, Segoe/system
sans for chrome, Consolas/Courier for the document) — **no CDN fonts**: offline and
intermittently connected terminals are a named deployment target, and nothing on the page
may depend on the network except the API itself (pinned by test). The committed frontend
may self-host **EB Garamond/Lato** (OFL, the design-system's law/government pairing); the
document pane's alignment must never depend on a downloadable font.

Layout: single column, ~76ch, document width. The form reads as a paper schedule —
Part I (Dates), Part II (Case and offence), Part III (Declarations and affirmations) — with
`fieldset`/`legend`, not cards. Motion: near-none (150ms button transitions only, behind
`prefers-reduced-motion`).

## Hard constraints (all carried from existing decisions — binding on any future frontend)

1. **No colour, icon, badge or tick encodes status** (D-035; D-068 §4's symmetric alarm
   bar). Colour is cheaper on screen, so this binds harder here than on paper. The
   interactive blue appears identically for every outcome. Enforced by test: no
   ✓/✗/⚠/badge glyphs in the page.
2. **Both verdict strings render in full.** No "Eligible / Not eligible" shorthand —
   enforced by test on the page source and satisfied structurally by rendering the
   canonical document.
3. **Flags and per-offence working always visible** — the whole canonical document renders;
   no `<details>`, no disclosure toggles. The working is the product.
4. **DETAINED_BEYOND_MAXIMUM at the top, in words** — the canonical document's boxed block
   already sits above everything; rendering the document verbatim preserves it.
5. **No aggregate dashboard.** One case at a time; no counts of entitled persons exist
   anywhere in the API either.
6. **`case_list_verified` / `prior_conviction_verified` never pre-ticked**; each checkbox
   states what is being affirmed at the point of affirmation. Enforced by test.
7. **No chat interface, no model on any path reaching the engine.** The API accepts typed
   facts and returns computed documents; stated on the page footer.
8. **The reviewer field renders empty and cannot be auto-filled** — it lives inside the
   canonical document, which the UI cannot edit.
9. **The uniformity line and the source-inventory line appear wherever a maximum is
   displayed** — both are inside the canonical document; any future view that extracts a
   maximum out of the document must carry both lines with it.
10. **The zero-rows / synthetic-fixtures state is unmissable** — the `data_warning` from
    every API response renders as a black-bordered, bold, full-width box above the
    document, and the page loads `/v1/meta`'s warning before anything is computed.

## The two conflicts, surfaced for Abhishek — not resolved here

* **Stack:** the Extended Abstract specifies **React**; the engineering brief specifies
  **server-first** (M7's stub line: "Drop React, ship a server-rendered form"). D-058 makes
  this his call. The demonstrator is deliberately neutral (plain HTML + `fetch`) and says so
  on the page. **→ RULED 2026-08-26 (D-084): server-rendered first**; the EA divergence is
  recorded on the D-027 pattern, and React remains addable later over the unchanged API.
* **D-030 × D-073:** the multilingual requirement (English/Hindi/Telugu UI at M7) collides
  with the stdlib PDF writer's WinAnsi-only encoding, which cannot carry Devanagari or
  Telugu script. If UI languages ever reach the *documents* rather than the chrome, D-073's
  no-dependency choice must be revisited (a font-embedding PDF writer or an approved
  library). If multilingualism stays UI-chrome-only (D-030's letter: "Input parsing stays
  English"), the collision does not arise. His call, recorded in D-077.
  **→ RULED 2026-08-26 (D-087): English-only documents, multilingual interface chrome
  only — a recorded scope limit. The collision is closed; a shaping-engine PDF path needs
  its own decision entry if ever revisited.**


## Narrow screens and the 78-column pane (measured; the trade-off is Abhishek's)

At the pane's 13.3px monospace, 78 columns need ≈ 620px including padding; a 375px phone
viewport therefore pans the document horizontally **inside its frame** (the page itself
never scrolls horizontally). The alternatives each break something: shrink-to-fit puts the
type at ≈ 7–8px (illegible); soft-wrapping destroys the fixed layout's alignment — the boxed
urgent block, the column structure — so the pane would no longer show the byte-exact
artefact; a second narrow-width canonical rendering means two regression artefacts and
forfeits the single source of truth. **RULED (Abhishek, 2026-08-19): panning stays** — the
byte-exact pane is the property that lets the UI be trusted. The ruling holds only because
DETAINED_BEYOND_MAXIMUM now also renders as page chrome above the pane (one flag restated
outside the artefact), so nothing safety-critical hides behind the horizontal scroll; and
the PDF path gives full-fidelity output on narrow devices (paginated A4, no panning).

## Stack recommendation on record

Server-first (recommended 2026-08-19; **RULED by Abhishek 2026-08-26 — D-084**):
low-spec offline-capable targets, no Node toolchain, and a central element the UI cannot
edit. The divergence from the Extended Abstract's React line is recorded explicitly in
D-077's addendum rather than left as a silent contradiction.

## Multilingual, at its real size

Devanagari and Telugu require a **text shaping engine** (conjunct formation, matra
reordering, glyph substitution) — not merely a font with the right codepoints. Embedding a
font in the stdlib PDF writer is insufficient. D-030's language work must never be scheduled
as a font swap; if document-level multilingualism is required, D-073 is revisited as a
shaping problem with a dependency decision attached.
