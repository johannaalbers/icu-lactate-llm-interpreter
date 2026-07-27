#!/usr/bin/env python3
"""
check_phi.py - scan a repository for MIMIC-III patient-level data before publishing.

Usage:
    python3 check_phi.py .                 # scan a whole repo
    python3 check_phi.py Report/foo.pdf    # scan one file

Exit code 0 = clean, 1 = findings. Suitable for a pre-commit hook or CI step.

Covers: .Rmd .R .qmd .ipynb .py .pdf .csv .txt, plus flags any committed
.RData/.rds file (which this script cannot inspect but which frequently
carries patient-level objects).

This is a safety net, not a guarantee. It cannot read data baked into images,
so also eyeball any figure that plots per-patient labels.
"""

import sys
import os
import re
import json
import zipfile

ID_COLS = r"(subject_id|hadm_id|icustay_id|row_id|SUBJECT_ID|HADM_ID|ICUSTAY_ID|ROW_ID)"

# Hardcoded identifier, e.g. subject_id == 17796
HARDCODED_ID = re.compile(ID_COLS + r"\s*==\s*[0-9]{3,}")

# Row-printing calls on a data frame in R
R_ROW_PRINT = re.compile(r"\b(glimpse|head|tail|View)\s*\(")

# glimpse-style output lines: ## $ hadm_id <int> 145834, 150750, ...
GLIMPSE_OUT = re.compile(r"\$\s*" + ID_COLS + r"\s*<")

# A tabular line containing an ID column header
ID_HEADER = re.compile(ID_COLS)

# Long runs of ID-like integers (MIMIC ids are 5-6 digits)
ID_RUN = re.compile(r"\b\d{5,6}\b(?:\s*,\s*\b\d{5,6}\b){3,}")

SKIP_DIRS = {".git", "node_modules", ".Rproj.user", "__pycache__", ".ipynb_checkpoints"}

# This script contains example identifier patterns in its own regexes and
# docstring, so it must not scan itself.
SELF = os.path.realpath(__file__)


def add(findings, path, sev, msg, detail=""):
    findings.append((path, sev, msg, detail.strip()[:180]))


def scan_text(path, text, findings, is_source):
    for m in HARDCODED_ID.finditer(text):
        line = text[: m.start()].count("\n") + 1
        add(findings, path, "HIGH", f"hardcoded patient identifier (line {line})", m.group(0))

    for m in GLIMPSE_OUT.finditer(text):
        line = text[: m.start()].count("\n") + 1
        add(findings, path, "HIGH", f"glimpse()/str() output with identifier (line {line})",
            text[m.start(): m.start() + 90])

    for m in ID_RUN.finditer(text):
        line = text[: m.start()].count("\n") + 1
        add(findings, path, "HIGH", f"run of identifier-like integers (line {line})",
            m.group(0))

    if is_source:
        for m in R_ROW_PRINT.finditer(text):
            line = text[: m.start()].count("\n") + 1
            add(findings, path, "REVIEW", f"row-printing call (line {line})",
                text[m.start(): m.start() + 70])


def scan_ipynb(path, findings):
    try:
        nb = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        add(findings, path, "REVIEW", f"could not parse notebook: {e}")
        return
    for i, cell in enumerate(nb.get("cells", [])):
        src = "".join(cell.get("source", []))
        scan_text(f"{path}[cell {i} src]", src, findings, is_source=True)
        for out in cell.get("outputs", []):
            t = out.get("text") or out.get("data", {}).get("text/plain") or ""
            if isinstance(t, list):
                t = "".join(t)
            if t and ID_HEADER.search(t):
                add(findings, path, "HIGH",
                    f"cell {i} OUTPUT contains identifier column", t[:120])
            if t:
                scan_text(f"{path}[cell {i} out]", t, findings, is_source=False)


def scan_pdf(path, findings):
    try:
        import pdfplumber
    except ImportError:
        add(findings, path, "REVIEW", "pdfplumber not installed; PDF not scanned")
        return
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception as e:
        add(findings, path, "REVIEW", f"could not read PDF: {e}")
        return
    scan_text(path, text, findings, is_source=False)


def scan_csv(path, findings):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            header = f.readline()
            body = "".join(f.readline() for _ in range(5))
    except Exception:
        return
    if ID_HEADER.search(header):
        add(findings, path, "HIGH", "CSV header contains an identifier column", header)
    scan_text(path, body, findings, is_source=False)


def main(target):
    findings = []
    files = []
    if os.path.isfile(target):
        files = [target]
    else:
        for root, dirs, names in os.walk(target):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            files += [os.path.join(root, n) for n in names]

    for path in files:
        if os.path.realpath(path) == SELF:
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext in (".rdata", ".rda", ".rds"):
            add(findings, path, "HIGH",
                "binary R data file committed - inspect for patient-level objects")
        elif ext == ".ipynb":
            scan_ipynb(path, findings)
        elif ext == ".pdf":
            scan_pdf(path, findings)
        elif ext == ".csv":
            scan_csv(path, findings)
        elif ext in (".rmd", ".r", ".qmd", ".py", ".txt", ".md"):
            try:
                scan_text(path, open(path, encoding="utf-8", errors="replace").read(),
                          findings, is_source=ext in (".rmd", ".r", ".qmd", ".py"))
            except Exception:
                pass

    high = [f for f in findings if f[1] == "HIGH"]
    review = [f for f in findings if f[1] == "REVIEW"]

    if high:
        print("\nHIGH - do not publish until resolved")
        print("=" * 62)
        for p, _, m, d in high:
            print(f"  {p}\n    {m}\n    {d}\n")
    if review:
        print("\nREVIEW - check output is aggregate, not row-level")
        print("=" * 62)
        for p, _, m, d in review:
            print(f"  {p}\n    {m}  {d}")

    print("\n" + "=" * 62)
    print(f"Scanned {len(files)} files. HIGH: {len(high)}  REVIEW: {len(review)}")
    if not high:
        print("No high-severity findings. Still eyeball figures with per-patient labels.")
    return 1 if high else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
