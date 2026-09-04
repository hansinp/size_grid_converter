---
name: size-grid-converter
description: Extract graded size specs from tech-pack .xlsx workbooks into a size_guide.csv size grid. Use when the user points at spec sheets, fit comment workbooks, or tech packs (often attached to an email) and wants the measurements pulled into a size guide CSV.
---

# Size grid converter

Pull graded size specs out of tech-pack workbooks and write them into a
`size_guide.csv` size grid.

Both formats are fixed and never change: the inputs are tech-pack `.xlsx`
workbooks containing a graded-spec sheet, and the output is the 26-column CSV
set out below. Everything you need to know about both is in this file — you
never need to open the destination CSV or any other document to understand the
shape of the work.

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

A wrong number in a size chart is invisible to everyone downstream: nobody can
tell it was a guess, and it ends up cutting fabric. A question costs the user
five seconds.

### What the script decides for you

`scripts/extract_specs.py` does all the mechanical work and classifies every
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
can see it.

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

If the user pointed at local files, use them. If they pointed at an email
("this email has the files"), use the **Microsoft 365 connector** to find the
message and download its `.xlsx` attachments into a working directory.

The connector must be authorized first. If its mail tools aren't available,
call `mcp__claude_ai_Microsoft_365__authenticate`, give the user the URL, and
wait for them to finish before continuing. Search by whatever the user gave you
— sender, subject, date, or style name — and confirm which message you found
before downloading anything.

### 2. Extract, one workbook at a time

```bash
uv run --with openpyxl python scripts/extract_specs.py "<workbook>.xlsx" \
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
  warns another sheet scored close, confirm with the user. Force one with
  `--sheet "<name>"`.
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
uv run --with openpyxl python scripts/write_rows.py /tmp/extraction.json \
    --csv <destination>.csv \
    --answer dress_waist=15 \
    --answer dress_hips=17
```

The destination is whichever size guide CSV the user named. If they didn't name
one, ask. Add `--dry-run` first if you want to show the user the rows before
they land.

`write_rows.py` refuses to write while any ASK column is unanswered, and rejects
an answer that isn't one of the candidate rows — so it cannot be talked into a
guess. It reads the column order from the destination's own header, and replaces
any existing rows for that SKU in place, so re-running a workbook is safe and
corrections are cheap.

### 5. Report back

Tell the user, per workbook: the SKU, the sheet used, which POM row filled each
column, which cells were left blank, and anything the script warned about.
Mention any measurement that wasn't an exact sixteenth of an inch — that usually
means the source cell holds a formula result that needs a human eye.

## Teaching it a new label wording

When a workbook uses a label the extractor doesn't recognise, a column comes
back MISSING even though the measurement is right there. Fix that by adding the
wording to that column's `include` list in `reference/pom_aliases.json`, which
is the script's configuration — you don't need to read it to run the workflow,
only to extend it.

Add wordings, not tie-breakers. A change that makes a previously ambiguous
column resolve itself silently is a regression, not an improvement.
