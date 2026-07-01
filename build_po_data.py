#!/usr/bin/env python3
"""One-time build step: parse college PO source documents (.docx) into a
structured JSON dataset (po_data.json) that the app loads at runtime.

WHY: Programme Outcomes are fixed reference data. Rather than have the AI read a
Word document on every generation (slow, costs tokens, non-deterministic), we
parse each document ONCE here into po_data.json and look it up instantly at
runtime. Re-run this script whenever a source document is added or updated.

USAGE:
    python build_po_data.py                 # build from the SOURCES below
    python build_po_data.py path.docx=science_arts:branched   # ad-hoc override

Output: po_data.json in the repo root.

Dataset shape:
{
  "science_arts": {                 # a "branched" type: many programmes
    "mode": "branched",
    "branches": {
      "bsc_mpc": {"label": "...", "stream": "science", "pos": [["PO1","Name","stmt"], ...]},
      ...
    }
  },
  "engineering": {                  # a "single" type: one PO set
    "mode": "single",
    "pos": [["PO1","Name","stmt"], ...]
  }
}
"""
import json
import os
import re
import sys
import zipfile
import html

# ── Source documents ──────────────────────────────────────────────────────────
# Map college_type -> (docx_path, mode). mode is "branched" (many programmes in
# one document, one PO block per programme) or "single" (one PO set for the type).
# Add new entries here as documents for other college types are shared.
SOURCES = {
    "science_arts": ("POs/PO-ScienceAndArtsDegreeColleges.docx", "branched"),
    "engineering":  ("POs/PO-Engineering.docx",                  "single"),
    "medical":      ("POs/PO-Medical.docx",                      "single"),
    "dental":       ("POs/PO-Dental COlleges.docx",              "single"),
    "law":          ("POs/PO-Law colleges.docx",                 "single"),
    "pharmacy":     ("POs/PO-Pharmacy.docx",                     "single"),
    "management":   ("POs/PO-MBA Program Outcomes.docx",         "single"),
    "architecture": ("POs/PO-Architecture and Planning.docx",    "single"),
    "agriculture":  ("POs/PO-Agriculture and Allied Sciences.docx", "single"),
}

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "po_data.json")

# For branched types, map each programme to a PO framework "stream". Derived from
# the branch abbreviation prefix; B.A programmes use the arts framework, B.Sc the
# science framework. (Only affects display/grouping, not the parsed POs.)
_ARTS_ABBREVS = {"CEP", "HEC", "HEP", "PPE", "EPS", "HSP", "JSP", "ESP", "EGS", "PSG"}


def _asciify(s: str) -> str:
    """Replace common non-ASCII punctuation with plain ASCII (see encoding note
    in project memory: user-visible strings must be plain ASCII)."""
    repl = {
        "–": "-", "—": "-", "‘": "'", "’": "'",
        "“": '"', "”": '"', "…": "...", " ": " ",
        "→": "->", "≤": "<=", "≥": ">=", "×": "x",
        "’": "'",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s.encode("ascii", "ignore").decode("ascii")


def _docx_lines(path: str) -> list[str]:
    """Return the document's paragraphs as a list of stripped, ASCII text lines."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = xml.replace("</w:p>", "\n")
    text = re.sub(r"<[^>]+>", "", xml)
    text = html.unescape(text)
    return [_asciify(l).strip() for l in text.split("\n") if _asciify(l).strip()]


# A branch header ends with "Program Outcomes (POs)" / "Programme Outcomes (POs)".
_BRANCH_RE = re.compile(r"^(?P<title>.+?)\s*[-–]\s*Program(?:me)?\s+Outcomes\s*\(POs\)\s*$")
# A PO line: "PO-1:", "PO 1:", "PO -2:", or discipline-prefixed "AP-PO1:", "AG-PO1:".
# The "... - Key Elements" variant is skipped.
_PO_RE = re.compile(r"^(?:[A-Z]{1,4}-)?PO[\s-]*(\d+):\s*(?P<rest>.+?)\s*$")
# First all-caps acronym (2+ letters) in a title -> programme abbreviation.
_ABBREV_RE = re.compile(r"\b([A-Z]{2,})\b")


def _abbrev(title: str) -> str:
    m = _ABBREV_RE.search(title)
    return m.group(1) if m else ""


def _slug(title: str) -> str:
    """B.Sc. MPC (...) -> bsc_mpc ; B.A./B.Sc. ESP (...) -> basc_esp."""
    ab = _abbrev(title).lower()
    prefix = "ba" if title.lstrip().startswith("B.A") else "bsc"
    if title.lstrip().startswith("B.A.") and "B.Sc" in title:
        prefix = "basc"
    return f"{prefix}_{ab}" if ab else prefix


def _parse_po_blocks(lines: list[str]) -> list[dict]:
    """Split lines into PO definitions. Returns list of [key, name, statement].

    Handles two document layouts:
      A) name and statement on separate lines:
           PO-1: Scientific Knowledge
           Apply the knowledge of ...
      B) name and statement on one line, colon-separated:
           PO-1: Engineering knowledge: Apply the knowledge of ...
    "PO-N: ... Key Elements" header lines and their bullet lists are skipped.
    """
    pos = []
    seen = set()
    for i, line in enumerate(lines):
        m = _PO_RE.match(line)
        if not m or "Key Elements" in line:
            continue
        num = int(m.group(1))
        rest = m.group("rest").strip()
        # Layout B: "Name: Statement" on one line (statement part is a real sentence).
        name, sep, tail = rest.partition(":")
        if sep and len(tail.strip()) >= 25:
            name, statement = name.strip(), tail.strip()
        else:
            # Layout A: statement is on the next non-empty line.
            name = rest
            statement = lines[i + 1].strip() if i + 1 < len(lines) else ""
        # Strip stray leading punctuation/numbering left in some documents
        # (e.g. "PO-12: . Life-long learning" -> "Life-long learning").
        name = re.sub(r"^[\W\d_]+", "", name).strip()
        key = f"PO{num}"
        if key not in seen and name:
            seen.add(key)
            pos.append([key, name, statement])
    pos.sort(key=lambda p: int(p[0][2:]))
    return pos


def parse_branched(lines: list[str]) -> dict:
    """Parse a document containing many programme PO blocks."""
    # Find branch header positions.
    headers = [(i, m.group("title").strip())
               for i, l in enumerate(lines)
               for m in [_BRANCH_RE.match(l)] if m]
    branches = {}
    for idx, (start, title) in enumerate(headers):
        end = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        block = lines[start + 1:end]
        pos = _parse_po_blocks(block)
        if not pos:
            continue
        code = _slug(title)
        stream = "arts" if _abbrev(title) in _ARTS_ABBREVS else "science"
        # Later duplicates overwrite earlier ones (documents repeat some blocks).
        branches[code] = {"label": title, "stream": stream, "pos": pos}
    return {"mode": "branched", "branches": branches}


def parse_single(lines: list[str]) -> dict:
    """Parse a document that defines a single PO set for the whole type."""
    return {"mode": "single", "pos": _parse_po_blocks(lines)}


def _backfill(ctype: str, pos: list) -> list:
    """Fill any PO key missing from a document with the curated hardcoded set,
    so a gap in a source document (e.g. Engineering merges PO-9 & PO-11) never
    produces an incomplete PO framework at runtime."""
    try:
        from generate_po_mapping import POS_BY_TYPE
    except Exception:
        return pos
    fallback = POS_BY_TYPE.get(ctype)
    if not fallback:
        return pos
    have = {p[0] for p in pos}
    added = []
    for key, name, desc in fallback:
        if key not in have:
            pos.append([key, name, _asciify(desc)])
            added.append(key)
    if added:
        print(f"         backfilled {ctype} from curated set: {', '.join(added)}")
    pos.sort(key=lambda p: int(p[0][2:]))
    return pos


def build(sources: dict) -> dict:
    data = {}
    for ctype, (path, mode) in sources.items():
        if not os.path.exists(path):
            print(f"  [skip] {ctype}: file not found -> {path}")
            continue
        lines = _docx_lines(path)
        section = parse_branched(lines) if mode == "branched" else parse_single(lines)
        if mode == "branched":
            n = len(section["branches"])
            print(f"  [ok]   {ctype}: {n} branches parsed")
        else:
            section["pos"] = _backfill(ctype, section["pos"])
            print(f"  [ok]   {ctype}: {len(section['pos'])} POs parsed")
        data[ctype] = section
    return data


def main():
    sources = dict(SOURCES)
    # ad-hoc overrides:  path.docx=ctype:mode
    for arg in sys.argv[1:]:
        if "=" in arg:
            path, spec = arg.split("=", 1)
            ctype, _, mode = spec.partition(":")
            sources[ctype] = (path, mode or "single")

    print("Building po_data.json ...")
    data = build(sources)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=True)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
