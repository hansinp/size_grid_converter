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
