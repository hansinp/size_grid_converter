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
