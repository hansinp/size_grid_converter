# size-grid-converter

A Claude Code skill that extracts graded size specs from tech-pack `.xlsx`
workbooks and writes them into a `size_guide.csv` size grid.

Point it at spec sheets — local files, or attachments on an email it can reach
through the Microsoft 365 connector — and it fills in the size guide, asking you
about the measurements that are genuinely ambiguous and nothing else.

```
you:  this email has the spec sheets, pull them into size_guide.csv
claude: found 3 workbooks. ALIVIA05 (top) resolved on its own.
        ELEN07 has two waist rows and two hip rows — which do you want?
        KATHERINE07 has two hip rows — which do you want?
```

## What it automates, and what it doesn't

The extractor does every mechanical thing: finding the graded-spec sheet among
twenty-odd sheets, reading the style name, working out the garment type,
matching Points of Measurement to CSV columns, and converting decimal inches to
the fractions the size guide uses.

It deliberately does **not** decide anything it is unsure about. Where two POM
rows both match a column, you get asked — spec sheets disagree with each other,
one dress recording the hip at the high hip and the next at the low hip. The
same goes for every other judgement: which attachment, which sheet, which style
name, which garment type, or a number that looks wrong. Anything ambiguous is
put to you directly rather than guessed at and flagged afterwards.

The writer refuses to write until you've answered, and refuses answers that
aren't one of the candidates. A wrong number in a size chart is invisible
downstream; a question takes five seconds.

## Install

Requires Claude Code, and either [`uv`](https://docs.astral.sh/uv/) or a Python
3 with `openpyxl` installed (`pip install openpyxl`).

Clone the repo, then make the skill visible to Claude Code by symlinking it into
your skills directory:

```bash
git clone https://github.com/hansinp/size_grid_converter.git ~/projects/size_grid_converter
mkdir -p ~/.claude/skills
ln -s ~/projects/size_grid_converter ~/.claude/skills/size-grid-converter
```

For one project only, symlink into that project instead:

```bash
mkdir -p .claude/skills
ln -s ~/projects/size_grid_converter .claude/skills/size-grid-converter
```

A symlink means `git pull` updates the installed skill. Copy the directory
instead if you'd rather pin it.

Check it registered by asking Claude to `/size-grid-converter`, or just describe
the job — the skill's description matches on spec sheets, tech packs and size
guides.

### Email attachments

To let it pull workbooks straight off an email, add the **Microsoft 365**
connector in Claude and authorize it. Without it the skill still works fine on
local files; you just download the attachments yourself first.

## Use it directly

The scripts are useful on their own, without an agent:

```bash
# See what a workbook contains and what's ambiguous
uv run --with openpyxl python scripts/extract_specs.py "ELEN08 FIT COMMENT.xlsx"

# Extract to JSON, then write the rows once you've decided
uv run --with openpyxl python scripts/extract_specs.py "ELEN08 FIT COMMENT.xlsx" \
    --out /tmp/elen.json
uv run --with openpyxl python scripts/write_rows.py /tmp/elen.json \
    --csv size_guide.csv --answer dress_waist=15 --answer dress_hips=17
```

Useful flags: `--sheet` forces a graded sheet by name, `--sku` overrides the
style name, `--dry-run` prints the rows without writing, and
`--answer <column>=blank` leaves a column empty on purpose.

Re-running a workbook replaces that SKU's rows in place, so corrections are
cheap.

## Layout

| Path | What it is |
| --- | --- |
| `SKILL.md` | the skill — workflow, the ask-don't-guess rule, and the full format spec |
| `scripts/extract_specs.py` | workbook → JSON report of POM candidates per column |
| `scripts/write_rows.py` | report + answers → CSV rows |
| `reference/pom_aliases.json` | POM label patterns per column — edit to teach new wordings |
| `cowork/SKILL.md` | **generated** single-file build for Claude Cowork |
| `cowork/preamble.md` | the Cowork-only setup section |
| `scripts/build_cowork_skill.py` | builds `cowork/SKILL.md`; `--check` verifies it |

### The Cowork build

Claude Cowork has no repo checkout, so it needs the skill as one self-contained
document that recreates the scripts on first run. `cowork/SKILL.md` is that
document, and it is **generated** — never edit it directly:

```bash
python3 scripts/build_cowork_skill.py           # rebuild it
python3 scripts/build_cowork_skill.py --check   # verify it is current
```

The build inlines the real `scripts/` and `reference/` files, rewrites paths to
the working-directory layout Cowork uses, and drops the YAML frontmatter that
only Claude Code needs. `--check` fails if the file is stale and also round-trips
the embedded blocks back out, comparing them byte-for-byte against the sources —
so an embedded copy cannot silently drift. Run it after touching either script.

`SKILL.md` is self-contained: the 26-column header, the garment families, the
number format and worked examples all live in the prompt, so the agent never
opens another file to understand the job. `pom_aliases.json` is the extractor's
configuration, read by the script rather than the agent.

The destination CSV is not in this repo — point the scripts at wherever your
size guide lives with `--csv`. Neither are the reference tech-pack workbooks or
the regression harness that uses them: those are real tech packs carrying
factory names, designer names and unreleased season specs, so they stay local to
whoever has them.

## Teaching it new label wordings

When a workbook writes a measurement in words the extractor doesn't know, that
column comes back MISSING even though the number is right there. Add the wording
to the column's `include` list in `reference/pom_aliases.json`.

Add wordings, not tie-breakers. If a change makes an ambiguous column resolve
itself silently, that's a regression rather than an improvement — the whole point
is that a human decides between two plausible measurements.

## Status

`dress` and `tops` mappings are verified against three real styles and reproduce
a known-good size guide byte for byte.

`bottoms` and `jumpsuit` mappings are a first pass with no reference style to
check against. The extractor flags them UNVERIFIED and the skill asks you to
confirm every column the first time you run one.

The Microsoft 365 email step has not been exercised end to end — it needs the
connector authorized on the account that receives the tech packs.

## Licence

Proprietary — copyright Velvet Inc., all rights reserved. See `LICENSE`. The
repository is public for convenience of distribution, which is not a grant of
any right to use it.
