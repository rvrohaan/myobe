"""
parse_profiles.py — Format profile registry for parse_template_paper.

Each profile describes the regex patterns and parsing strategy for one
institutional question paper format.  Built-in profiles live in
format_profiles/builtin.json; custom profiles from colleges/users are
stored as format_profiles/custom_<id>.json files.

Public API
----------
get_profiles()              -> list[dict]   sorted by priority desc
reload_profiles()
get_profile(id)             -> dict | None
add_custom_profile(profile) -> None         (saves to disk, reloads)
delete_custom_profile(id)   -> bool
list_profiles()             -> list[dict]   summary rows for the UI
score_slots(slots)          -> float [0..1] confidence scorer
parse_with_llm(text)        -> list[dict]   LLM extraction (opt-in)
"""

import json
import os
import re
from pathlib import Path

PROFILES_DIR = Path(__file__).parent / "format_profiles"

_REGISTRY: list[dict] | None = None


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def _load() -> list[dict]:
    profiles: list[dict] = []

    builtin = PROFILES_DIR / "builtin.json"
    if builtin.exists():
        try:
            data = json.loads(builtin.read_text("utf-8"))
            profiles.extend(data if isinstance(data, list) else [data])
        except Exception:
            pass

    for path in sorted(PROFILES_DIR.glob("custom_*.json")):
        try:
            data = json.loads(path.read_text("utf-8"))
            items = data if isinstance(data, list) else [data]
            profiles.extend(items)
        except Exception:
            pass

    return sorted(profiles, key=lambda p: -p.get("priority", 0))


def get_profiles() -> list[dict]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _load()
    return _REGISTRY


def reload_profiles() -> None:
    global _REGISTRY
    _REGISTRY = _load()


def get_profile(profile_id: str) -> dict | None:
    return next((p for p in get_profiles() if p["id"] == profile_id), None)


def add_custom_profile(profile: dict) -> None:
    """Validate, persist, and reload a custom profile."""
    required = {"id", "name", "parser_type"}
    missing = required - profile.keys()
    if missing:
        raise ValueError(f"Profile missing required fields: {missing}")
    if profile["parser_type"] not in ("table", "qblock"):
        raise ValueError("parser_type must be 'table' or 'qblock'")

    pid = re.sub(r"[^\w\-]", "_", profile["id"])
    path = PROFILES_DIR / f"custom_{pid}.json"
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    reload_profiles()


def delete_custom_profile(profile_id: str) -> bool:
    pid = re.sub(r"[^\w\-]", "_", profile_id)
    path = PROFILES_DIR / f"custom_{pid}.json"
    if path.exists():
        path.unlink()
        reload_profiles()
        return True
    return False


def list_profiles() -> list[dict]:
    """Return summary rows suitable for the management UI."""
    builtins = {
        p["id"]
        for p in json.loads((PROFILES_DIR / "builtin.json").read_text("utf-8"))
    } if (PROFILES_DIR / "builtin.json").exists() else set()

    return [
        {
            "id":          p["id"],
            "name":        p["name"],
            "description": p.get("description", ""),
            "priority":    p.get("priority", 0),
            "parser_type": p.get("parser_type", "table"),
            "builtin":     p["id"] in builtins,
        }
        for p in get_profiles()
    ]


# ---------------------------------------------------------------------------
# Confidence scorer
# ---------------------------------------------------------------------------

def score_slots(slots: list) -> float:
    """Compute a confidence score [0..1] for a parsed slot list.

    Weights:
      40 % — CO coverage  (fraction of slots that have a CO value)
      30 % — Quantity     (normalised: 6+ slots = full credit)
      30 % — Text quality (normalised: avg ≥ 80 chars = full credit)
    """
    content = [s for s in slots if not s.get("is_or")]
    if not content:
        return 0.0
    co_cov  = sum(1 for s in content if s.get("co")) / len(content)
    qty     = min(1.0, len(content) / 6)
    avg_len = sum(len(s.get("original_text", "")) for s in content) / len(content)
    quality = min(1.0, avg_len / 80)
    return round(0.4 * co_cov + 0.3 * qty + 0.3 * quality, 3)


# ---------------------------------------------------------------------------
# LLM fallback  (opt-in — only runs when ANTHROPIC_API_KEY is set)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a question paper parser. Extract every question or task that has
an associated marks/weightage value. Return ONLY a valid JSON array — no
markdown, no explanation, nothing else.

Each element must be:
{
  "qnum":  "1",        // question number string, "" if absent
  "sub":   "a",        // sub-question label, "" if absent
  "text":  "...",      // full question text (required)
  "co":    "CO1",      // course outcome code, "" if absent
  "marks": 10,         // integer marks (required)
  "unit":  "UNIT - I"  // unit/section name, "General" if absent
}

Rules:
• marks must be a positive integer.
• Omit OR-divider rows — only include actual questions/tasks.
• If a question has multiple parts listed separately, include each part.
• Do not include rubric criteria rows unless they clearly describe a task."""


def parse_with_llm(text: str) -> list[dict]:
    """Call Claude API (Haiku) to extract slots from arbitrary paper formats.

    Returns an empty list if ANTHROPIC_API_KEY is not set or on any error.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []
    try:
        import anthropic
    except ImportError:
        return []

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=45.0, max_retries=3)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text[:8000]}],
        )
        raw = resp.content[0].text.strip()
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return []
        items = json.loads(m.group(0))
        slots: list[dict] = []
        for item in items:
            marks = item.get("marks")
            txt   = str(item.get("text", "")).strip()
            if not txt or not marks:
                continue
            try:
                marks = int(marks)
            except (TypeError, ValueError):
                continue
            if marks < 1:
                continue
            slots.append({
                "is_or":         False,
                "unit":          str(item.get("unit") or "General"),
                "qnum":          str(item.get("qnum") or ""),
                "sub":           str(item.get("sub")  or ""),
                "marks":         marks,
                "co":            str(item.get("co")   or ""),
                "po":            "",
                "original_text": txt[:400],
            })
        return slots
    except Exception:
        return []
