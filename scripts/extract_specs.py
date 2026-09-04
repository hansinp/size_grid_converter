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
        "    uv run --with openpyxl python scripts/extract_specs.py ...\n"
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
