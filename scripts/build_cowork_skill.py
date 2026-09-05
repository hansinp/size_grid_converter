#!/usr/bin/env python3
"""Generate the single-file Claude Cowork build of the skill.

Cowork has no repo checkout, so the skill has to carry its own scripts and
recreate them on first run. This builds that file from the real sources rather
than a hand-kept copy, which is the whole point: an embedded copy that drifts
from scripts/ fails silently in exactly the environment that has no repo to
check against.

    build_cowork_skill.py            # write cowork/SKILL.md
    build_cowork_skill.py --check    # verify it is current, write nothing

--check is the one to run in CI or before committing. It fails if the generated
file is stale, and it also round-trips: it parses the embedded blocks back out
and compares them byte-for-byte against the files on disk.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "SKILL.md"
PREAMBLE = REPO_ROOT / "cowork" / "preamble.md"
OUTPUT = REPO_ROOT / "cowork" / "SKILL.md"

# Files embedded into the generated skill, in the order they appear, with the
# path each one must be written to in the Cowork working directory.
EMBEDDED = [
    ("scripts/extract_specs.py", "size-grid-converter/scripts/extract_specs.py", "python"),
    ("scripts/write_rows.py", "size-grid-converter/scripts/write_rows.py", "python"),
    ("reference/pom_aliases.json", "size-grid-converter/reference/pom_aliases.json", "json"),
]

# Repo-relative paths become working-directory paths, and `python` becomes
# `python3` because Cowork environments don't reliably alias it. Order matters:
# the longest, most specific patterns must run first.
REWRITES = [
    ("python scripts/", "python3 size-grid-converter/scripts/"),
    ("`scripts/", "`size-grid-converter/scripts/"),
    ("`reference/", "`size-grid-converter/reference/"),
]

GENERATED_NOTICE = (
    "<!-- GENERATED FILE. Do not edit.\n"
    "     Built from SKILL.md + cowork/preamble.md + the scripts, by\n"
    "     scripts/build_cowork_skill.py. Edit those and rebuild. -->\n"
)

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n+", re.DOTALL)


def strip_frontmatter(text):
    """Cowork takes the document as prose, not as a skill manifest."""
    return FRONTMATTER_RE.sub("", text, count=1)


def fence_for(text):
    """A fence long enough that nothing inside the file can close it early."""
    longest = max((len(m) for m in re.findall(r"^`{3,}", text, re.MULTILINE)), default=0)
    return "`" * max(3, longest + 1)


def build():
    body = strip_frontmatter(SOURCE.read_text())
    for old, new in REWRITES:
        body = body.replace(old, new)

    # Slot the preamble in before the first section, so the title keeps its
    # intro paragraphs and Setup still comes well ahead of step 1.
    lines = body.split("\n")
    first_section = next(i for i, line in enumerate(lines) if line.startswith("## "))
    body = (
        "\n".join(lines[:first_section])
        + PREAMBLE.read_text().strip()
        + "\n\n"
        + "\n".join(lines[first_section:])
    )

    parts = [
        GENERATED_NOTICE,
        body.rstrip("\n"),
        "",
        "## Embedded files",
        "",
        "Exact source for the three files referenced above. Copy each block's",
        "content verbatim to the named path during Setup — never retype or",
        "summarise it.",
        "",
    ]
    for source_path, target_path, language in EMBEDDED:
        content = (REPO_ROOT / source_path).read_text()
        fence = fence_for(content)
        parts += [
            f"### `{target_path}`",
            "",
            f"{fence}{language}",
            content.rstrip("\n"),
            fence,
            "",
        ]
    return "\n".join(parts)


def extract_embedded(generated):
    """Parse the embedded blocks back out, for the round-trip check."""
    found = {}
    pattern = re.compile(
        r"^### `(?P<path>[^`]+)`\n\n(?P<fence>`{3,})\w*\n(?P<body>.*?)\n(?P=fence)$",
        re.DOTALL | re.MULTILINE,
    )
    for match in pattern.finditer(generated):
        found[match.group("path")] = match.group("body") + "\n"
    return found


def check(generated):
    problems = []

    if not OUTPUT.exists():
        problems.append(f"{OUTPUT.relative_to(REPO_ROOT)} does not exist; run without --check")
    else:
        current = OUTPUT.read_text()
        if current != generated:
            diff = difflib.unified_diff(
                current.splitlines(keepends=True),
                generated.splitlines(keepends=True),
                fromfile="cowork/SKILL.md (on disk)",
                tofile="cowork/SKILL.md (rebuilt)",
                n=1,
            )
            problems.append(
                "cowork/SKILL.md is stale. Rebuild it. Difference:\n"
                + "".join(list(diff)[:40])
            )

    # Round-trip: what a Cowork agent would write out must equal what we ship.
    embedded = extract_embedded(generated)
    for source_path, target_path, _ in EMBEDDED:
        original = (REPO_ROOT / source_path).read_text()
        recovered = embedded.get(target_path)
        if recovered is None:
            problems.append(f"{target_path}: no embedded block found in the generated file")
        elif recovered != original:
            problems.append(
                f"{target_path}: embedded block does not round-trip to {source_path} "
                f"({len(recovered)} chars vs {len(original)})"
            )
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify, don't write")
    args = parser.parse_args(argv)

    generated = build()

    if args.check:
        problems = check(generated)
        if problems:
            print("FAIL  cowork/SKILL.md", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        embedded = ", ".join(path for _, path, _ in EMBEDDED)
        print(f"PASS  cowork/SKILL.md is current and round-trips ({embedded})")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generated)
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(generated.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
