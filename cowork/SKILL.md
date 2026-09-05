<!-- GENERATED FILE. Do not edit.
     Built from SKILL.md + cowork/preamble.md + the scripts, by
     scripts/build_cowork_skill.py. Edit those and rebuild. -->

# Size grid converter

Pull graded size specs out of tech-pack workbooks and write them into a
`size_guide.csv` size grid.

Both formats are fixed and never change: the inputs are tech-pack `.xlsx`
workbooks containing a graded-spec sheet, and the output is the 26-column CSV
set out below. Everything you need to know about both is in this file — you
never need to open the destination CSV or any other document to understand the
shape of the work.
## Setup

This skill's mechanical work is done by two Python scripts and a JSON alias
file, embedded verbatim at the end of this document so the skill is a single
self-contained file. Before step 1 of the workflow, check whether
`size-grid-converter/scripts/extract_specs.py` already exists in the current
working directory.

If it exists, skip straight to the workflow below.

If it doesn't, create these three files now, copying each one's content exactly
— including the shebang line, comments, and trailing newline — from the matching
fenced block under **Embedded files** at the end of this document. Do not
paraphrase, reformat, or "clean up" the code:

- `size-grid-converter/scripts/extract_specs.py`
- `size-grid-converter/scripts/write_rows.py`
- `size-grid-converter/reference/pom_aliases.json`

Then run `chmod +x size-grid-converter/scripts/*.py`.

`openpyxl` is required. Try `uv run --with openpyxl python3 <script> ...` first,
as in the commands below. If `uv` isn't available in this environment, fall back
to `pip install --break-system-packages openpyxl` once, then invoke the scripts
with plain `python3`.

## The one rule that matters

**Automate only what is unambiguous. If anything is ambiguous or you are unsure
about it, ask the user directly.**

This is the whole design of this skill, and it is not limited to the ambiguous
columns the script detects. It applies to every judgement in the workflow: which
email, which attachment, which sheet, which style name, which garment type,
which POM row, whether a number looks wrong. Whenever you would have to assume
something to keep going, stop and ask instead.

Ask directly, in plain terms, showing what you're choosing between. Don't guess
and flag it afterwards, don't pick the more likely option and mention it in
passing, and don't quietly narrow the job to the parts you were sure about. The
user is sitting there and expects to be asked — that is why this runs
interactively.

Investigating a warning yourself — opening the runner-up sheet to see whether
it's really a blank template, checking whether an internal-code-looking SKU has
a friendlier alternative nearby — is good diligence and often worth doing. But
it does not replace asking. Bring what you found to the user and let them make
the call, even when you're confident you already know the answer. Deciding for
them because the investigation felt conclusive is the same mistake as guessing
without looking.

A wrong number in a size chart is invisible to everyone downstream: nobody can
tell it was a guess, and it ends up cutting fabric. A question costs the user
five seconds.

### What the script decides for you

`size-grid-converter/scripts/extract_specs.py` does all the mechanical work and classifies every
target column as one of three things:

- **AUTO** — exactly one Point of Measurement (POM) row matched. Use it. Don't ask.
- **MISSING** — no POM row matched, so the garment doesn't have that measurement
  (a sleeveless dress has no sleeve length). Leave the cell blank. Don't ask.
- **ASK** — two or more POM rows matched. **Stop and ask the user which row to
  use.** Show them each candidate's label and its values across the sizes.

Never resolve an ASK yourself, and never add a heuristic to the alias file to
make ASKs resolve silently. Spec sheets genuinely disagree with each other — one
dress records the hip at the high hip, the next at the low hip.

### Always ask, never assume

Beyond the ASK columns, stop and ask the user whenever:

- More than one email or attachment could be the one they meant.
- The report warns that another sheet scored close to the one it picked, or the
  sheet it picked isn't obviously the graded spec sheet.
- The SKU looks like an internal factory code (`CS8447`, `CO8541`) rather than a
  style name, or the workbook offers more than one candidate style name.
- The garment family couldn't be settled from the description, or the
  description is vague enough that two families would both fit.
- The family is marked UNVERIFIED (`bottoms`, `jumpsuit`) — confirm every column
  with the user, not just the ambiguous ones.
- The sizes on the sheet aren't the ones you expected, or a POM row is missing a
  value for some sizes.
- A measurement isn't an exact sixteenth of an inch, or a value looks
  implausible for what it claims to measure.
- A column comes back MISSING but the user's request implies it should be there.
- Anything else leaves you unsure. This list is not exhaustive — the rule is the
  rule, and an unlisted doubt is still a doubt.

Batch the questions for one workbook into a single exchange rather than
interrogating the user one field at a time, and give them the information they
need to answer: the labels, the numbers, and what the difference means where you
can see it. If you're working through several workbooks in one session, it's
fine to batch all of their questions into one round of asks rather than stopping
after each file.

## The output format

26 columns, one row per SKU per size, CRLF line endings, UTF-8, no quoting
(values contain spaces but never commas, so nothing needs quotes):

```
sku,size,size.tops_length,size.tops_bust,size.tops_chest,size.tops_armhole,size.tops_sleeve_length,size.tops_sweep,size.bottoms_length,size.bottoms_hips,size.bottoms_waist,size.bottoms_inseam,size.bottoms_front_rise,size.bottoms_back_rise,size.bottoms_leg_opening,size.dress_length,size.dress_bust,size.dress_waist,size.dress_hips,size.dress_sleeve_length,size.jumpsuit_bust,size.jumpsuit_waist,size.jumpsuit_armhole,size.jumpsuit_sleeve_length,size.jumpsuit_inseam,size.jumpsuit_leg_opening
```

### Garment families

Each row fills exactly one family's column group and leaves the other 20-odd
cells empty. The family is detected from the COVER page's `DESCRIPTION:` field:

| Family | Its columns | Detected from words like |
| --- | --- | --- |
| `tops` | `tops_length`, `tops_bust`, `tops_chest`, `tops_armhole`, `tops_sleeve_length`, `tops_sweep` | TOP, BLOUSE, SHIRT, TEE, SWEATER, JACKET, CARDIGAN, TANK |
| `bottoms` | `bottoms_length`, `bottoms_hips`, `bottoms_waist`, `bottoms_inseam`, `bottoms_front_rise`, `bottoms_back_rise`, `bottoms_leg_opening` | PANT, SHORT, SKIRT, JEAN, TROUSER, LEGGING |
| `dress` | `dress_length`, `dress_bust`, `dress_waist`, `dress_hips`, `dress_sleeve_length` | DRESS, GOWN, CAFTAN |
| `jumpsuit` | `jumpsuit_bust`, `jumpsuit_waist`, `jumpsuit_armhole`, `jumpsuit_sleeve_length`, `jumpsuit_inseam`, `jumpsuit_leg_opening` | JUMPSUIT, ROMPER, OVERALL, PLAYSUIT |

`tops` splits bust and chest into two columns. `dress` and `jumpsuit` have a
single `_bust` column that accepts either a BUST or a CHEST measurement. A
garment with no such measurement leaves the cell blank — a top whose spec sheet
records a chest but no bust gets `tops_chest` filled and `tops_bust` empty.

Only `dress` and `tops` are verified against known-good output. `bottoms` and
`jumpsuit` are a first pass; the extractor reports them UNVERIFIED.

### Number format

Decimal inches become whole inches plus a fraction, where **the fraction
occupies a fixed four-character field** (shown here with `·` for space):

| In the spreadsheet | In the CSV |
| --- | --- |
| `47.25` | `47 1/4` |
| `40` | `40····` |
| `8.875` | `8 7/8` |
| `19.125` | `19 1/8` |

So: `{whole}` followed by either `" n/d"` or four spaces. Fractions are reduced
and limited to sixteenths. The trailing spaces are load-bearing — the size guide
has them and downstream consumers rely on them. `write_rows.py` handles all of
this; never hand-format a value.

### Sizes and SKU

One row per size, ordered `XXS, XS, S, M, L, XL, XXL, 2XL, 3XL`, filtered to
whatever the graded sheet actually has.

The SKU is the style name recorded **inside** the workbook, read from the graded
sheet's `STYLE:` field and falling back to the COVER page. It is never taken
from the filename, which drifts: a file named `ALIVIA07 TOP COMMENTS 5-19-26`
contains style `ALIVIA05`, and `ELEN08 SHIPMENT FIT COMMENT` contains `ELEN07`.
Some COVER pages carry an internal factory code (`CS8447`, `CO8541`) in the
`STYLE:` field instead of a style name; the extractor flags anything shaped like
a code so you can confirm it rather than write it.

### What good output looks like

Three real styles, verified end to end. Note the POM labels differ across
workbooks for the same column, and that a sleeveless dress leaves its sleeve
column blank:

| Column | `ELEN07` (dress) | `ALIVIA05` (top) | `KATHERINE07` (dress) |
| --- | --- | --- | --- |
| `_length` | BODY LENGTH frm h.p.s | FRONT LENGTH FROM HPS TO HEM EDGE | BODY LENGTH FROM NK HPS |
| `_bust` / `_chest` | BUST 1" below arm hole | CHEST CIRCUMFERENCE 1" DOWN FROM UNDERARM | CHEST 1" BELOW ARMHOLE-FLAT |
| `_waist` | WAIST at TOP of SMOCKING STITCH | *(no waist column for tops)* | WAIST - 15" BELOW HPS |
| `_hips` | HIGHT HIP 16" below armhole | *(no hips column for tops)* | LOW HIP -7" BELOW BODICE SEAM |
| `_sleeve_length` | SLV LENGTH/ Raglan | SLEEVE LENGTH | *(blank — sleeveless)* |

The resulting rows, for `ELEN07` size XS and `ALIVIA05` size XL:

```
ELEN07,XS,,,,,,,,,,,,,,47 1/4,40    ,23 1/2,46 1/2,23    ,,,,,,
ALIVIA05,XL,24 3/4,,37    ,8 7/8,26    ,9 3/4,,,,,,,,,,,,,,,,,,
```

`ELEN07`'s waist and hips were both ASK columns — its sheet offered waist at the
top *and* bottom of the smocking stitch, and both a high and a low hip. The user
picked. `KATHERINE07`'s hips were an ASK too, and the user picked the opposite
kind (low, not high), which is exactly why this is never inferred.

## Workflow

### 1. Get the workbooks onto disk

Work out where the workbooks actually are before doing anything else. If more
than one plausible source or file is on the table, ask which one they mean
rather than guessing.

- **Already attached to this conversation, or a path they gave you** — read them
  directly; they're reachable on disk.
- **On the user's computer** — if a device bridge is available and a folder is
  connected, work with the files there, staging them into the working directory
  if a step needs a library only available here. If no computer is connected,
  ask them to attach the files or connect the folder.
- **In an email** ("this email has the files") — use the **Microsoft 365
  connector**, if it's available in this session, to find the message. It must
  be authorized first; if its mail tools aren't available, call
  `mcp__claude_ai_Microsoft_365__authenticate`, give the user the URL, and wait.
  Search by whatever they gave you — sender, subject, date, or style name — and
  confirm which message, and which files within it, before downloading anything.

When the workbooks come from email, check whether they're real attachments or
just links, because the right move differs and the two look alike at a glance:

- **A real attachment** — the message's attachment list is genuinely populated,
  not just text in the body. Download it directly.
- **A SharePoint/OneDrive link pasted into the body** — common, and easy to
  mistake for an attachment, so check the attachment list rather than assuming.
  Do not treat a connector's document-reading call as a substitute for getting
  the file: it reads a workbook's sheets in file order up to a fixed output
  size, it cannot be pointed at a specific sheet, and a workbook with many
  template and cover-page sheets ahead of the real graded sheet may never reach
  it however many times you retry. Worse, even a fully successful read returns
  the workbook as *text*, never the file, so `extract_specs.py` still can't run
  on it and you'd be reduced to reconstructing the extraction by hand — slower
  and more error-prone than the script it replaces. Don't sink more than one or
  two attempts into it. Instead, if a browser automation tool is available and
  already signed into the user's own Microsoft account, drive it to the link and
  download the file — never enter credentials or sign the user in yourself, only
  use a session that is already authenticated. Failing that, resolve the direct
  file link, hand it to the user, and ask them to download it and attach it here
  or drop it in a connected folder. Either way, a browser download lands on the
  user's own device, not your workspace: it still has to reach you before
  extraction can start.

If a file is too large to attach or stage, say so plainly and ask how they'd
like to get it to you — a smaller re-export, a connected folder — rather than
retrying a transfer that will keep failing.

### 2. Extract, one workbook at a time

```bash
uv run --with openpyxl python3 size-grid-converter/scripts/extract_specs.py "<workbook>.xlsx" \
    --out /tmp/extraction.json
```

The script prints a report and writes the full JSON. Read the report and check
three things before going further:

- **sku** — the style name read from the graded sheet. If the script flags it as
  looking like an internal code, ask the user for the real style name and pass
  it later with `--sku`.
- **sheet** — which sheet it read. These workbooks carry blank grading
  templates (`grade tops`, `QC MEASUREMENT SHEET`) alongside the real graded
  sheet, and the real one is named inconsistently: `SPECS`, `GRADED SPECS.`,
  `GRADING`. One workbook may hold both a single-size fit-comment sheet and a
  graded sheet; only the graded one belongs in the size guide. If the report
  warns another sheet scored close, confirm with the user — don't settle it
  yourself and just report the outcome, even if you're confident after looking.
  Force one with `--sheet "<name>"`.
- **family** — which column group gets filled. If the script couldn't settle it,
  ask. If it's UNVERIFIED, confirm every column, not just the ambiguous ones.

### 3. Ask about the ASK columns

For each ASK column, put the candidates to the user with their measurements, and
say what the difference means where you can see it. Ask about all of a
workbook's ambiguous columns in one go rather than one at a time.

> `dress_hips` has two candidates:
> - row 31, HIGH HIP @ BOTTOM BODICE SEAM — XS 30, S 32, M 33 1/2, L 35 1/2, XL 38
> - row 34, LOW HIP 7" BELOW BOTTOM BODICE SEAM, EXTENDED FLAT — XS 56, S 58, M 59 1/2, L 61 1/2, XL 64
>
> Which should go in the size guide?

If the user says the measurement doesn't belong in the guide at all, that's
`--answer <column>=blank`.

### 4. Write the rows

```bash
uv run --with openpyxl python3 size-grid-converter/scripts/write_rows.py /tmp/extraction.json \
    --csv <destination>.csv \
    --answer dress_waist=15 \
    --answer dress_hips=17
```

The destination is whichever size guide CSV the user named. If they didn't name
one, ask. If it doesn't exist yet, ask whether to create it: `write_rows.py`
reads the column order from an existing header, so a new file needs the
26-column header row above written to it first, and nothing else. Add
`--dry-run` if you want to show the user the rows before they land.

`write_rows.py` refuses to write while any ASK column is unanswered, and rejects
an answer that isn't one of the candidate rows — so it cannot be talked into a
guess. It reads the column order from the destination's own header, and replaces
any existing rows for that SKU in place, so re-running a workbook is safe and
corrections are cheap.

### 5. Verify, then report back

Before telling the user you're done, check what you're about to hand over:
re-run `write_rows.py --dry-run` and diff it against what actually landed in the
destination, and spot-check a couple of the fraction conversions against the
source decimals. This is cheap, and it's what catches a formatting slip before
it ships rather than after it's in a factory's hands.

Tell the user, per workbook: the SKU, the sheet used, which POM row filled each
column, which cells were left blank, and anything the script warned about.
Mention any measurement that wasn't an exact sixteenth of an inch — that usually
means the source cell holds a formula result that needs a human eye.

If the destination CSV lives in a connected folder on the user's computer, write
the update back there. If it only ever existed in this session's working
directory, deliver the updated CSV as a file so they can save it.

## Teaching it a new label wording

When a workbook uses a label the extractor doesn't recognise, a column comes
back MISSING even though the measurement is right there. Fix that by adding the
wording to that column's `include` list in `size-grid-converter/reference/pom_aliases.json`, which
is the script's configuration — you don't need to read it to run the workflow,
only to extend it.

Add wordings, not tie-breakers. A change that makes a previously ambiguous
column resolve itself silently is a regression, not an improvement.

## Embedded files

Exact source for the three files referenced above. Copy each block's
content verbatim to the named path during Setup — never retype or
summarise it.

### `size-grid-converter/scripts/extract_specs.py`

```python
#!/usr/bin/env python3
"""Read a tech-pack .xlsx and report the graded size specs it contains.

This script makes no judgement calls. It locates the graded-spec sheet, reads
every Point of Measurement (POM) row, and for each target column in
size_guide.csv reports which POM rows are candidates:

  auto       exactly one candidate  -> safe to fill in without asking
  ambiguous  two or more candidates -> the agent must ask the human which to use
  missing    no candidates          -> the cell is left blank

Usage:
    extract_specs.py <workbook.xlsx> [--out extraction.json] [--sheet NAME]
                     [--aliases reference/pom_aliases.json] [--quiet]

Exit status is 0 even when columns are ambiguous; ambiguity is an expected
outcome that the caller resolves, not an error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import openpyxl
except ModuleNotFoundError:  # pragma: no cover
    sys.exit(
        "openpyxl is required. Run this script with:\n"
        "    uv run --with openpyxl python3 <path to this script> ...\n"
        "or install it with: pip install openpyxl"
    )

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ALIASES = REPO_ROOT / "reference" / "pom_aliases.json"

# A cell holding an internal factory code rather than a human style name.
INTERNAL_CODE_RE = re.compile(r"^[A-Z]{2}\d{3,5}$")


def normalise(text: str) -> str:
    """Uppercase and collapse whitespace so alias patterns match predictably."""
    return re.sub(r"\s+", " ", str(text)).strip().upper()


def as_number(value):
    """Return value as a float if it is numeric, else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().replace('"', "")
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def find_size_header(ws, size_tokens):
    """Find the row that labels the size columns.

    Returns (row_index, {size: column_index}) or (None, None). Requires each
    size to sit in its own cell, which is what distinguishes a real graded
    header from a COVER page's "SIZES: XS, S, M, L, XL" summary cell.
    """
    token_set = {normalise(t) for t in size_tokens}
    best = (None, None, 0)
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 40)):
        found = {}
        for cell in row:
            if cell.value is None:
                continue
            text = normalise(cell.value)
            if text in token_set and text not in found:
                found[text] = cell.column
        if len(found) >= 3 and len(found) > best[2]:
            best = (row[0].row, found, len(found))
    if best[0] is None:
        return None, None
    return best[0], best[1]


def find_label_column(ws, header_row, size_columns):
    """The column holding POM labels: leftmost text column left of the sizes."""
    limit = min(size_columns.values())
    counts = {}
    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
        for cell in row:
            if cell.column >= limit or cell.value is None:
                continue
            if isinstance(cell.value, str) and cell.value.strip():
                counts[cell.column] = counts.get(cell.column, 0) + 1
    if not counts:
        return None
    # Prefer the column with the most labels; ties go to the leftmost.
    return min(counts, key=lambda col: (-counts[col], col))


def read_pom_rows(ws, header_row, size_columns, label_column, lining_pattern):
    """Read every POM row below the header.

    A row with a label but no numeric size values is treated as a section
    heading (e.g. "LINING") and applied to the rows beneath it.
    """
    lining_re = re.compile(lining_pattern, re.IGNORECASE)
    rows = []
    section = None
    for row_idx in range(header_row + 1, ws.max_row + 1):
        raw_label = ws.cell(row=row_idx, column=label_column).value
        label = str(raw_label).strip() if raw_label is not None else ""
        values = {}
        for size, col in size_columns.items():
            number = as_number(ws.cell(row=row_idx, column=col).value)
            if number is not None:
                values[size] = number
        if not label and not values:
            continue
        if label and not values:
            section = label
            continue
        if not label:
            continue
        rows.append(
            {
                "row": row_idx,
                "label": label,
                "normalised": normalise(label),
                "section": section,
                "in_lining_section": bool(section and lining_re.search(section)),
                "values": values,
            }
        )
    return rows


def score_sheet(pom_rows, sheet_name):
    """How likely this sheet is the graded-spec sheet."""
    populated = sum(1 for r in pom_rows if len(r["values"]) >= 3)
    bonus = 0
    name = normalise(sheet_name)
    if "GRAD" in name or "SPEC" in name:
        bonus += 10
    if "QC" in name or "PATTERN" in name or "BOM" in name:
        bonus -= 20
    return populated + bonus


def locate_graded_sheet(wb, size_tokens, lining_pattern, forced=None):
    """Pick the graded-spec sheet, returning it plus the runners-up."""
    candidates = []
    names = [forced] if forced else wb.sheetnames
    for name in names:
        if name not in wb.sheetnames:
            sys.exit(f"No sheet named {name!r}. Sheets: {wb.sheetnames}")
        ws = wb[name]
        header_row, size_columns = find_size_header(ws, size_tokens)
        if not size_columns:
            continue
        label_column = find_label_column(ws, header_row, size_columns)
        if label_column is None:
            continue
        pom_rows = read_pom_rows(
            ws, header_row, size_columns, label_column, lining_pattern
        )
        if not pom_rows:
            continue
        candidates.append(
            {
                "sheet": name,
                "header_row": header_row,
                "size_columns": size_columns,
                "label_column": label_column,
                "pom_rows": pom_rows,
                "score": score_sheet(pom_rows, name),
                "populated_rows": sum(1 for r in pom_rows if len(r["values"]) >= 3),
            }
        )
    if not candidates:
        return None, []
    candidates.sort(key=lambda c: -c["score"])
    return candidates[0], candidates[1:]


def read_labelled_value(ws, label_pattern, max_row=40, max_scan=6):
    """Find "LABEL: value", either inline in one cell or in a cell to the right."""
    pattern = re.compile(label_pattern, re.IGNORECASE)
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, max_row)):
        for cell in row:
            if not isinstance(cell.value, str):
                continue
            text = cell.value.strip()
            if not pattern.match(text):
                continue
            inline = re.sub(pattern, "", text, count=1).lstrip(" :\t")
            if inline:
                return inline.strip(), cell.coordinate
            for offset in range(1, max_scan + 1):
                neighbour = ws.cell(row=cell.row, column=cell.column + offset).value
                if neighbour is None:
                    continue
                if isinstance(neighbour, str) and neighbour.strip() in ("", "0", "\\"):
                    continue
                if isinstance(neighbour, str) and neighbour.strip():
                    return neighbour.strip(), f"{cell.coordinate}->{ws.cell(row=cell.row, column=cell.column + offset).coordinate}"
    return None, None


def resolve_sku(wb, graded):
    """The style name, preferring the graded sheet over the COVER page.

    The filename is deliberately never consulted: it drifts from the style name
    recorded inside the workbook (a file named ALIVIA07 holds style ALIVIA05).
    """
    ws = wb[graded["sheet"]]
    sku, where = read_labelled_value(ws, r"STYLE\b")
    notes = []
    source = f"sheet {graded['sheet']!r} {where}" if sku else None

    alternatives = []
    if "COVER" in wb.sheetnames:
        cover = wb["COVER"]
        cover_sku, cover_where = read_labelled_value(cover, r"STYLE\b")
        if cover_sku:
            alternatives.append({"value": cover_sku, "source": f"COVER {cover_where}"})
        # A friendlier style name often sits beside the internal code.
        for row in cover.iter_rows(min_row=1, max_row=12):
            for cell in row:
                if isinstance(cell.value, str):
                    text = cell.value.strip()
                    if (
                        text
                        and text != sku
                        and re.fullmatch(r"[A-Z]+\d{1,3}", text.upper())
                        and not INTERNAL_CODE_RE.match(text.upper())
                    ):
                        alternatives.append(
                            {"value": text, "source": f"COVER {cell.coordinate}"}
                        )

    if sku and INTERNAL_CODE_RE.match(normalise(sku)):
        notes.append(
            f"{sku!r} looks like an internal factory code, not a style name. "
            "Confirm the SKU with the human before writing."
        )
    if not sku:
        notes.append("No STYLE field found on the graded sheet. Ask the human.")

    # De-duplicate alternatives, dropping any equal to the chosen SKU.
    seen = set()
    unique = []
    for alt in alternatives:
        key = normalise(alt["value"])
        if key in seen or key == normalise(sku or ""):
            continue
        seen.add(key)
        unique.append(alt)

    return {"sku": sku, "source": source, "alternatives": unique, "notes": notes}


def resolve_description(wb, graded):
    for sheet in (["COVER"] if "COVER" in wb.sheetnames else []) + [graded["sheet"]]:
        value, where = read_labelled_value(wb[sheet], r"DESCRIPTION\b")
        if value and value not in ("0",):
            return value, f"{sheet} {where}"
    return None, None


def detect_family(description, families):
    """Match the description against each family's detect patterns."""
    if not description:
        return None, []
    text = normalise(description)
    hits = [
        name
        for name, spec in families.items()
        if any(re.search(p, text, re.IGNORECASE) for p in spec["detect"])
    ]
    return (hits[0] if len(hits) == 1 else None), hits


def resolve_columns(pom_rows, family_spec, aliases):
    """Classify each target column as auto / ambiguous / missing."""
    always = [re.compile(p, re.IGNORECASE) for p in aliases.get("exclude_always", [])]
    kind_excludes = aliases.get("kind_excludes", {})
    resolution = {}
    for column, rules in family_spec["columns"].items():
        includes = [re.compile(p, re.IGNORECASE) for p in rules["include"]]
        patterns = list(rules.get("exclude", []))
        patterns += kind_excludes.get(rules.get("kind"), [])
        excludes = [re.compile(p, re.IGNORECASE) for p in patterns] + always
        candidates = []
        for row in pom_rows:
            if row["in_lining_section"]:
                continue
            label = row["normalised"]
            if not any(rx.search(label) for rx in includes):
                continue
            if any(rx.search(label) for rx in excludes):
                continue
            if not row["values"]:
                continue
            candidates.append(
                {"row": row["row"], "label": row["label"], "values": row["values"]}
            )
        if len(candidates) == 1:
            status = "auto"
        elif not candidates:
            status = "missing"
        else:
            status = "ambiguous"
        resolution[column] = {
            "status": status,
            "chosen_row": candidates[0]["row"] if status == "auto" else None,
            "candidates": candidates,
        }
    return resolution


def build_report(path, aliases, forced_sheet=None):
    wb = openpyxl.load_workbook(path, data_only=True)
    graded, runners_up = locate_graded_sheet(
        wb, aliases["size_tokens"], aliases["lining_section_pattern"], forced_sheet
    )
    if graded is None:
        return {
            "source_file": str(path),
            "error": "No graded-spec sheet found (no sheet has separate XS/S/M/L/XL "
            "columns with numeric rows beneath them).",
            "sheets": wb.sheetnames,
        }

    close = [c for c in runners_up if graded["score"] - c["score"] <= 5]

    sku_info = resolve_sku(wb, graded)
    description, description_source = resolve_description(wb, graded)
    family, family_hits = detect_family(description, aliases["families"])

    report = {
        "source_file": str(path),
        "sheet": graded["sheet"],
        "sheet_alternatives": [
            {"sheet": c["sheet"], "populated_rows": c["populated_rows"]}
            for c in runners_up
        ],
        "header_row": graded["header_row"],
        "sizes": list(graded["size_columns"].keys()),
        "sku": sku_info["sku"],
        "sku_source": sku_info["source"],
        "sku_alternatives": sku_info["alternatives"],
        "notes": list(sku_info["notes"])
        + [
            f"Sheet {graded['sheet']!r} scored barely ahead of "
            f"{c['sheet']!r} ({c['populated_rows']} populated rows). Confirm the right "
            "sheet with the human."
            for c in close
        ],
        "description": description,
        "description_source": description_source,
        "garment_family": family,
        "garment_family_candidates": family_hits,
        "pom_row_count": len(graded["pom_rows"]),
        "pom_rows": [
            {k: v for k, v in row.items() if k != "normalised"}
            for row in graded["pom_rows"]
        ],
    }

    if family is None:
        report["notes"].append(
            f"Could not settle the garment family from description {description!r} "
            f"(matched: {family_hits or 'nothing'}). Ask the human."
        )
        report["resolution"] = {}
        return report

    family_spec = aliases["families"][family]
    report["family_verified"] = family_spec["verified"]
    if not family_spec["verified"]:
        report["notes"].append(
            f"The {family!r} column mapping has never been checked against a known-good "
            "output row. Confirm every column with the human before writing."
        )
    report["resolution"] = resolve_columns(graded["pom_rows"], family_spec, aliases)
    return report


def frac(value):
    """Render a decimal inch value the way a human reads a tape measure."""
    from fractions import Fraction

    whole = int(value)
    remainder = Fraction(value).limit_denominator(16) - whole
    if remainder == 0:
        return str(whole)
    return f"{whole} {remainder.numerator}/{remainder.denominator}"


def print_report(report):
    print(f"file        {Path(report['source_file']).name}")
    if "error" in report:
        print(f"ERROR       {report['error']}")
        print(f"sheets      {', '.join(report['sheets'])}")
        return
    print(f"sheet       {report['sheet']}  (header row {report['header_row']})")
    if report["sheet_alternatives"]:
        others = ", ".join(
            f"{c['sheet']} ({c['populated_rows']} rows)"
            for c in report["sheet_alternatives"]
        )
        print(f"  also graded: {others}")
    print(f"sku         {report['sku']}   [{report['sku_source']}]")
    if report["sku_alternatives"]:
        for alt in report["sku_alternatives"]:
            print(f"  alt:      {alt['value']}   [{alt['source']}]")
    print(f"description {report['description']}   [{report['description_source']}]")
    print(f"family      {report['garment_family']}", end="")
    if report.get("family_verified") is False:
        print("   (UNVERIFIED mapping)", end="")
    print()
    print(f"sizes       {', '.join(report['sizes'])}")
    print(f"pom rows    {report['pom_row_count']}")
    print()

    for column, info in report.get("resolution", {}).items():
        short = column.replace("size.", "")
        if info["status"] == "auto":
            candidate = info["candidates"][0]
            values = "  ".join(
                f"{s}={frac(v)}" for s, v in candidate["values"].items()
            )
            print(f"  AUTO      {short:22} <- row {candidate['row']} {candidate['label']!r}")
            print(f"                                   {values}")
        elif info["status"] == "missing":
            print(f"  MISSING   {short:22} (no matching POM row; cell left blank)")
        else:
            print(f"  ASK       {short:22} {len(info['candidates'])} candidates:")
            for candidate in info["candidates"]:
                values = "  ".join(
                    f"{s}={frac(v)}" for s, v in candidate["values"].items()
                )
                print(f"              row {candidate['row']:>3}  {candidate['label']}")
                print(f"                       {values}")

    if report["notes"]:
        print()
        for note in report["notes"]:
            print(f"  NOTE      {note}")

    asks = [c for c, i in report.get("resolution", {}).items() if i["status"] == "ambiguous"]
    print()
    if asks:
        print(f"{len(asks)} column(s) need a human decision: {', '.join(c.replace('size.', '') for c in asks)}")
    else:
        print("Nothing ambiguous; every column resolved on its own.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--out", type=Path, help="write the full report as JSON")
    parser.add_argument("--sheet", help="force a specific graded sheet by name")
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--quiet", action="store_true", help="suppress the text report")
    args = parser.parse_args(argv)

    if not args.workbook.exists():
        sys.exit(f"No such file: {args.workbook}")
    aliases = json.loads(args.aliases.read_text())
    report = build_report(args.workbook, aliases, args.sheet)

    if not args.quiet:
        print_report(report)
    if args.out:
        args.out.write_text(json.dumps(report, indent=2, default=str))
        if not args.quiet:
            print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `size-grid-converter/scripts/write_rows.py`

```python
#!/usr/bin/env python3
"""Turn an extraction report into size_guide.csv rows.

Takes the JSON produced by extract_specs.py, plus one --answer per ambiguous
column, and writes one CSV row per size. It refuses to write while any
ambiguous column is unanswered, so a guess can never reach the size guide.

Usage:
    write_rows.py extraction.json --csv size_guide.csv
                  [--answer size.dress_hips=17] [--answer size.dress_waist=blank]
                  [--sku ELEN07] [--dry-run]

Existing rows for the same SKU are replaced in place, which makes re-running
the same workbook safe. The destination's header row defines the column order;
this script never invents or reorders columns.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from fractions import Fraction
from pathlib import Path

# The fraction part occupies a fixed four-character field, so "40" is written
# "40    " and 47.25 is written "47 1/4". This matches the existing size guide
# exactly; downstream consumers rely on it.
FRACTION_FIELD = 4
MAX_DENOMINATOR = 16

SIZE_ORDER = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL"]


def format_measurement(value):
    """Render a decimal inch value as whole inches plus a padded fraction."""
    fraction = Fraction(value).limit_denominator(MAX_DENOMINATOR)
    exact = abs(float(fraction) - float(value)) < 1e-9
    whole = int(fraction)
    remainder = fraction - whole
    if remainder == 0:
        text = f"{whole}" + " " * FRACTION_FIELD
    else:
        text = f"{whole}" + f" {remainder.numerator}/{remainder.denominator}".ljust(
            FRACTION_FIELD
        )
    return text, exact


def read_header(csv_path):
    with csv_path.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    if header[:2] != ["sku", "size"]:
        sys.exit(
            f"{csv_path} does not start with the expected 'sku,size' columns: {header[:2]}"
        )
    return header


def parse_answers(pairs):
    answers = {}
    for pair in pairs or []:
        if "=" not in pair:
            sys.exit(f"--answer expects COLUMN=ROW, got {pair!r}")
        column, value = pair.split("=", 1)
        column = column.strip()
        if not column.startswith("size."):
            column = f"size.{column}"
        value = value.strip().lower()
        if value in ("blank", "none", "skip", ""):
            answers[column] = None
        else:
            try:
                answers[column] = int(value)
            except ValueError:
                sys.exit(f"--answer {pair!r}: expected a POM row number or 'blank'")
    return answers


def choose_rows(report, answers):
    """Decide which POM row fills each column. Returns (chosen, problems)."""
    chosen = {}
    problems = []
    for column, info in report.get("resolution", {}).items():
        candidates = {c["row"]: c for c in info["candidates"]}
        if column in answers:
            row = answers[column]
            if row is None:
                continue
            if row not in candidates:
                offered = ", ".join(str(r) for r in candidates) or "none"
                problems.append(
                    f"{column}: answered row {row}, which is not a candidate "
                    f"(candidates: {offered})"
                )
                continue
            chosen[column] = candidates[row]
        elif info["status"] == "auto":
            chosen[column] = info["candidates"][0]
        elif info["status"] == "ambiguous":
            listing = "; ".join(
                f"row {c['row']} {c['label']!r}" for c in info["candidates"]
            )
            problems.append(
                f"{column}: {len(info['candidates'])} candidates and no --answer. "
                f"Ask the human, then pass --answer {column}=<row> "
                f"(or =blank to leave it empty). Candidates: {listing}"
            )
    return chosen, problems


def build_rows(report, header, chosen, sku):
    sizes = report["sizes"]
    ordered = [s for s in SIZE_ORDER if s in sizes] + [
        s for s in sizes if s not in SIZE_ORDER
    ]
    rows = []
    warnings = []
    for size in ordered:
        record = {"sku": sku, "size": size}
        for column, candidate in chosen.items():
            if size not in candidate["values"]:
                warnings.append(
                    f"{column}: POM row {candidate['row']} has no value for size {size}"
                )
                continue
            text, exact = format_measurement(candidate["values"][size])
            if not exact:
                warnings.append(
                    f"{column} {size}: {candidate['values'][size]} is not an exact "
                    f"1/{MAX_DENOMINATOR} inch, written as {text.strip()!r}"
                )
            record[column] = text
        unknown = set(record) - set(header)
        if unknown:
            sys.exit(f"Columns absent from the destination header: {sorted(unknown)}")
        rows.append([record.get(column, "") for column in header])
    return rows, warnings


def write_csv(csv_path, header, rows, sku):
    """Replace this SKU's rows in place, or append them if it is new."""
    with csv_path.open(newline="", encoding="utf-8") as handle:
        existing = list(csv.reader(handle))
    body = [r for r in existing[1:] if r and any(field.strip() for field in r)]

    kept = [r for r in body if r[0] != sku]
    replaced = len(body) - len(kept)
    if replaced:
        first = next(i for i, r in enumerate(body) if r[0] == sku)
        merged = kept[:first] + rows + kept[first:]
    else:
        merged = kept + rows

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(merged)
    csv_path.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    return replaced


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extraction", type=Path, help="JSON from extract_specs.py")
    parser.add_argument("--csv", type=Path, required=True, help="destination size guide")
    parser.add_argument("--answer", action="append", help="COLUMN=ROW or COLUMN=blank")
    parser.add_argument("--sku", help="override the SKU read from the workbook")
    parser.add_argument("--dry-run", action="store_true", help="print rows, write nothing")
    args = parser.parse_args(argv)

    report = json.loads(args.extraction.read_text())
    if "error" in report:
        sys.exit(f"Extraction failed: {report['error']}")

    sku = args.sku or report.get("sku")
    if not sku:
        sys.exit("No SKU in the extraction and no --sku given. Ask the human.")
    if not report.get("resolution"):
        sys.exit(
            "The extraction resolved no columns (garment family unsettled). "
            "Settle the family with the human and re-run extract_specs.py."
        )

    header = read_header(args.csv)
    answers = parse_answers(args.answer)

    unknown = set(answers) - set(report["resolution"])
    if unknown:
        sys.exit(f"--answer names columns this garment has no mapping for: {sorted(unknown)}")

    chosen, problems = choose_rows(report, answers)
    if problems:
        print("Cannot write yet:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    rows, warnings = build_rows(report, header, chosen, sku)
    blanks = [c for c, i in report["resolution"].items() if c not in chosen]

    for column, candidate in chosen.items():
        print(f"  {column.replace('size.', ''):22} row {candidate['row']:>3}  {candidate['label']}")
    for column in blanks:
        print(f"  {column.replace('size.', ''):22} (blank)")
    for warning in warnings:
        print(f"  WARNING {warning}")

    if args.dry_run:
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows(rows)
        print()
        print(buffer.getvalue(), end="")
        return 0

    replaced = write_csv(args.csv, header, rows, sku)
    verb = f"replaced {replaced}" if replaced else "appended"
    print(f"\n{verb} -> {len(rows)} rows for {sku} in {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `size-grid-converter/reference/pom_aliases.json`

```json
{
  "_comment": [
    "Maps size_guide.csv columns to the Points of Measurement (POM) labels used in tech-pack",
    "spec sheets. Patterns are case-insensitive regexes matched against the POM label after",
    "normalisation (uppercased, whitespace collapsed).",
    "",
    "A column resolves to 'auto' only when EXACTLY ONE POM row survives include-minus-exclude.",
    "Zero survivors means 'missing' (the cell is left blank). Two or more means 'ambiguous',",
    "and the agent must ask the human which row to use. Do not add tie-breaker priorities here",
    "to make ambiguous cases resolve themselves -- an ambiguous case is a question, not a guess.",
    "",
    "Rules are layered, and a row is dropped if ANY layer excludes it:",
    "  exclude_always  applied to every column; drops lining / under-dress duplicate rows,",
    "                  which some workbooks mark with a LINING section header and others",
    "                  mark inline in the label (e.g. 'BUST/under dress 1\" below arm hole').",
    "  kind_excludes   applied by the column's 'kind'. A girth column measures around the",
    "                  body, so a row whose label announces a LENGTH, DROP, HEIGHT, WIDTH or",
    "                  ACROSS measurement is never a candidate for it. This is what keeps",
    "                  'CF SKIRT LENGTH below waist seam to hem' out of the waist candidates.",
    "  include/exclude the column's own patterns.",
    "",
    "'verified' marks a family whose mapping has been checked against known-good output rows.",
    "Unverified families are reported as needing human confirmation for every column."
  ],

  "size_tokens": ["XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL"],

  "lining_section_pattern": "LINING|UNDER ?DRESS|UNDERLAY|UNDER ?LAYER",

  "exclude_always": ["\\bLINING\\b", "UNDER ?DRESS", "\\bUNDERLAY\\b", "UNDER ?LAYER"],

  "kind_excludes": {
    "girth": ["\\bLENGTH\\b", "\\bPLACEMENT\\b", "\\bDROP\\b", "\\bHEIGHT\\b", "\\bWIDTH\\b", "\\bACROSS\\b"],
    "length": ["\\bPLACEMENT\\b"]
  },

  "families": {
    "dress": {
      "verified": true,
      "verified_against": ["ELEN07", "KATHERINE07"],
      "detect": ["\\bDRESS\\b", "\\bGOWN\\b", "\\bCAFTAN\\b", "\\bKAFTAN\\b"],
      "columns": {
        "size.dress_length": {
          "kind": "length",
          "include": ["\\bBODY LENGTH\\b", "\\bFRONT LENGTH\\b"],
          "exclude": ["^C\\.?B\\b", "^BACK\\b", "^CENTER BACK\\b", "\\bBACK LENGTH\\b", "SKIRT", "SLIT", "BODICE", "SLEEVE", "\\bSLV\\b"]
        },
        "size.dress_bust": {
          "kind": "girth",
          "include": ["\\bBUST\\b", "\\bCHEST\\b"],
          "exclude": []
        },
        "size.dress_waist": {
          "kind": "girth",
          "include": ["\\bWAIST\\b"],
          "exclude": []
        },
        "size.dress_hips": {
          "kind": "girth",
          "include": ["\\bHIPS?\\b"],
          "exclude": []
        },
        "size.dress_sleeve_length": {
          "kind": "length",
          "include": ["\\bSLEEVE LENGTH\\b", "\\bSLV LENGTH\\b"],
          "exclude": ["\\bUNDER ?SLEEVE\\b", "\\bUNDER ?SLV\\b", "\\bCAP\\b"]
        }
      }
    },

    "tops": {
      "verified": true,
      "verified_against": ["ALIVIA05"],
      "detect": ["\\bTOP\\b", "\\bBLOUSE\\b", "\\bSHIRT\\b", "\\bTEE\\b", "\\bT-SHIRT\\b", "\\bSWEATER\\b", "\\bJACKET\\b", "\\bCARDIGAN\\b", "\\bTANK\\b", "\\bBODYSUIT\\b"],
      "columns": {
        "size.tops_length": {
          "kind": "length",
          "include": ["\\bBODY LENGTH\\b", "\\bFRONT LENGTH\\b"],
          "exclude": ["^C\\.?B\\b", "^BACK\\b", "^CENTER BACK\\b", "\\bBACK LENGTH\\b", "SKIRT", "SLIT", "BODICE", "SLEEVE", "\\bSLV\\b"]
        },
        "size.tops_bust": {
          "kind": "girth",
          "include": ["\\bBUST\\b"],
          "exclude": []
        },
        "size.tops_chest": {
          "kind": "girth",
          "include": ["\\bCHEST\\b"],
          "exclude": []
        },
        "size.tops_armhole": {
          "kind": "girth",
          "include": ["\\bARM ?HOLE\\b"],
          "exclude": ["CURVE", "\\bEDGE\\b", "^FR(ON)?T\\b", "^B(A)?CK\\b", "CONTRAST", "PANEL"]
        },
        "size.tops_sleeve_length": {
          "kind": "length",
          "include": ["\\bSLEEVE LENGTH\\b", "\\bSLV LENGTH\\b"],
          "exclude": ["\\bUNDER ?SLEEVE\\b", "\\bUNDER ?SLV\\b", "\\bCAP\\b"]
        },
        "size.tops_sweep": {
          "kind": "girth",
          "include": ["\\bSWEEP\\b"],
          "exclude": []
        }
      }
    },

    "bottoms": {
      "verified": false,
      "verified_against": [],
      "detect": ["\\bPANT\\b", "\\bPANTS\\b", "\\bSHORT\\b", "\\bSHORTS\\b", "\\bSKIRT\\b", "\\bJEAN\\b", "\\bJEANS\\b", "\\bTROUSER\\b", "\\bLEGGING\\b", "\\bCULOTTE\\b"],
      "columns": {
        "size.bottoms_length": {
          "kind": "length",
          "include": ["\\bOUT ?SEAM\\b", "\\bSIDE LENGTH\\b", "\\bBODY LENGTH\\b", "\\bFRONT LENGTH\\b"],
          "exclude": ["^C\\.?B\\b", "^BACK\\b", "\\bIN ?SEAM\\b"]
        },
        "size.bottoms_hips": {
          "kind": "girth",
          "include": ["\\bHIPS?\\b"],
          "exclude": []
        },
        "size.bottoms_waist": {
          "kind": "girth",
          "include": ["\\bWAIST\\b"],
          "exclude": ["\\bBAND\\b"]
        },
        "size.bottoms_inseam": {
          "kind": "length",
          "include": ["\\bIN ?SEAM\\b"],
          "exclude": ["\\bSLEEVE\\b", "\\bSLV\\b"]
        },
        "size.bottoms_front_rise": {
          "kind": "length",
          "include": ["\\bFR(ON)?T RISE\\b", "^FR(ON)?T\\b.*\\bRISE\\b"],
          "exclude": []
        },
        "size.bottoms_back_rise": {
          "kind": "length",
          "include": ["\\bB(A)?CK RISE\\b", "^B(A)?CK\\b.*\\bRISE\\b"],
          "exclude": []
        },
        "size.bottoms_leg_opening": {
          "kind": "girth",
          "include": ["\\bLEG OPENING\\b", "\\bHEM OPENING\\b", "\\bBOTTOM OPENING\\b"],
          "exclude": ["\\bSLEEVE\\b", "\\bSLV\\b"]
        }
      }
    },

    "jumpsuit": {
      "verified": false,
      "verified_against": [],
      "detect": ["\\bJUMPSUIT\\b", "\\bROMPER\\b", "\\bOVERALL\\b", "\\bPLAYSUIT\\b", "\\bCOVERALL\\b"],
      "columns": {
        "size.jumpsuit_bust": {
          "kind": "girth",
          "include": ["\\bBUST\\b", "\\bCHEST\\b"],
          "exclude": []
        },
        "size.jumpsuit_waist": {
          "kind": "girth",
          "include": ["\\bWAIST\\b"],
          "exclude": ["\\bBAND\\b"]
        },
        "size.jumpsuit_armhole": {
          "kind": "girth",
          "include": ["\\bARM ?HOLE\\b"],
          "exclude": ["CURVE", "\\bEDGE\\b", "^FR(ON)?T\\b", "^B(A)?CK\\b", "CONTRAST", "PANEL"]
        },
        "size.jumpsuit_sleeve_length": {
          "kind": "length",
          "include": ["\\bSLEEVE LENGTH\\b", "\\bSLV LENGTH\\b"],
          "exclude": ["\\bUNDER ?SLEEVE\\b", "\\bUNDER ?SLV\\b", "\\bCAP\\b"]
        },
        "size.jumpsuit_inseam": {
          "kind": "length",
          "include": ["\\bIN ?SEAM\\b"],
          "exclude": ["\\bSLEEVE\\b", "\\bSLV\\b"]
        },
        "size.jumpsuit_leg_opening": {
          "kind": "girth",
          "include": ["\\bLEG OPENING\\b", "\\bHEM OPENING\\b", "\\bBOTTOM OPENING\\b"],
          "exclude": ["\\bSLEEVE\\b", "\\bSLV\\b"]
        }
      }
    }
  }
}
```
