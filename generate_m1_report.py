"""Module 1 Comprehensive Report Generator.

Builds a DOCX report covering all 11 Module-1 deliverables:
  1.  Automatic CO Generation
  2.  Intelligent Question Bank Creation
  3.  Smart Question Paper (auto-generated sample)
  4.  Bloom's Taxonomy Compliance Check
  5.  CO Coverage Verification
  6.  Difficulty Level Analysis
  7.  Scenario & Case Study Analysis
  8.  Question Quality Index (QQI)
  9.  CO-wise Marks Distribution
 10.  OBE/NBA/NAAC/NEP Compliance Report
 11.  Accreditation Readiness Dashboard
"""

import re
import json
import datetime

# ── Bloom's action-verb mapping ───────────────────────────────────────────────
_BLOOM_LEVELS = {
    "remember":   ["define", "list", "recall", "state", "identify", "name", "recognise", "label"],
    "understand": ["explain", "describe", "summarise", "interpret", "classify", "compare", "illustrate"],
    "apply":      ["solve", "compute", "use", "implement", "demonstrate", "calculate", "execute", "apply"],
    "analyse":    ["analyse", "differentiate", "examine", "distinguish", "break down", "investigate"],
    "evaluate":   ["evaluate", "justify", "assess", "critique", "argue", "appraise", "defend", "judge"],
    "create":     ["design", "develop", "construct", "generate", "formulate", "plan", "produce", "build"],
}

_SCENARIO_KEYWORDS = [
    "scenario", "case study", "consider", "given that", "in a system",
    "suppose", "assume", "a company", "an organization", "discuss the",
    "analyse the following", "with reference to", "in context of",
    "real-world", "industry", "application of",
]

_DIRECT_VERBS = [
    r"^define\b", r"^list\b", r"^state\b", r"^what is\b",
    r"^name\b", r"^write\b", r"^give\b",
]


def _detect_bloom(text: str) -> str:
    t = text.lower()
    for level, verbs in reversed(list(_BLOOM_LEVELS.items())):
        if any(t.startswith(v) or f" {v} " in t for v in verbs):
            return level.capitalize()
    return "Remember"   # default fallback


def _is_scenario(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _SCENARIO_KEYWORDS)


def _is_direct(text: str) -> bool:
    t = text.lower().strip()
    return any(re.match(pat, t) for pat in _DIRECT_VERBS)


# ── Quantitative analytics (no AI needed) ────────────────────────────────────

def _compute_lab_analytics(cos: list, lab_tally: dict) -> dict:
    """Compute analytics for a lab course using experiment counts per CO."""
    co_nums   = {str(c["num"]) for c in cos}
    covered   = {k for k in lab_tally if lab_tally[k].get("exp", 0) > 0}
    uncovered = co_nums - covered
    coverage_pct = round(len(covered) / len(co_nums) * 100, 1) if co_nums else 0

    total_exp = sum(v.get("exp", 0) for v in lab_tally.values())

    co_marks  = {k: v.get("exp", 0) for k, v in lab_tally.items()}
    total_marks = sum(co_marks.values()) or 1

    qqi_scores = {}
    for c in cos:
        key   = str(c["num"])
        n_exp = lab_tally.get(key, {}).get("exp", 0)
        adequacy = min(100, n_exp / max(1, 3) * 100)   # expect ~3 experiments per CO
        qqi_scores[f"CO{key}"] = round(adequacy)
    overall_qqi = round(sum(qqi_scores.values()) / max(len(qqi_scores), 1))

    return {
        "covered": sorted(covered),
        "uncovered": sorted(uncovered),
        "coverage_pct": coverage_pct,
        "total_2": 0, "total_5": 0, "total_10": 0,
        "total_assign": 0, "total_quiz": 0,
        "total_exam": total_exp,
        "total_exp": total_exp,
        "diff_dist": {"Lab Experiments": total_exp},
        "co_marks": co_marks,
        "total_marks": total_marks,
        "scenario_count": 0, "direct_count": 0,
        "unclassified": 0, "total_analyzed": 0, "scenario_pct": 0,
        "qqi_scores": qqi_scores,
        "overall_qqi": overall_qqi,
        "is_lab": True,
    }


def compute_analytics(cos: list, co_tally: dict, raw_qb_text: str = "",
                      is_lab: bool = False, lab_tally: dict = None) -> dict:
    """Return all rule-based metrics derived from COs and QB tally."""
    if is_lab and lab_tally:
        return _compute_lab_analytics(cos, lab_tally)

    co_nums = {str(c["num"]) for c in cos}

    # --- CO Coverage ---
    covered = {k for k in co_tally if co_tally[k].get(2, 0) + co_tally[k].get(5, 0) + co_tally[k].get(10, 0) > 0}
    uncovered = co_nums - covered
    coverage_pct = round(len(covered) / len(co_nums) * 100, 1) if co_nums else 0

    # --- Difficulty distribution ---
    total_2  = sum(v.get(2,  0) for v in co_tally.values())
    total_5  = sum(v.get(5,  0) for v in co_tally.values())
    total_10 = sum(v.get(10, 0) for v in co_tally.values())
    total_assign = sum(v.get("assign", 0) for v in co_tally.values())
    total_quiz   = sum(v.get("quiz",   0) for v in co_tally.values())
    total_exam = total_2 + total_5 + total_10

    # Difficulty labels: 2-mark→Easy, 5-mark→Medium, 10-mark→Hard
    diff_dist = {
        "Easy (2-mark)":   total_2,
        "Medium (5-mark)": total_5,
        "Hard (10-mark)":  total_10,
    }

    # --- CO-wise marks distribution ---
    co_marks = {}
    for k, v in co_tally.items():
        co_marks[k] = v.get(2, 0) * 2 + v.get(5, 0) * 5 + v.get(10, 0) * 10
    total_marks = sum(co_marks.values()) or 1

    # --- Scenario analysis (from raw QB text) ---
    # Count ALL Q\d+. lines (exam + quiz) so unclassified stays non-negative
    scenario_count = 0
    direct_count   = 0
    total_analyzed = 0
    if raw_qb_text:
        for line in raw_qb_text.split("\n"):
            s = line.strip()
            if re.match(r"Q\d+\.", s):
                total_analyzed += 1
                text = re.sub(r"Q\d+\.\s*", "", s)
                text = re.sub(r"\[CO\d+\]", "", text).strip()
                if _is_scenario(text):
                    scenario_count += 1
                elif _is_direct(text):
                    direct_count += 1
    unclassified = max(0, total_analyzed - scenario_count - direct_count)
    scenario_pct = round(scenario_count / total_analyzed * 100, 1) if total_analyzed else 0

    # --- Rule-based QQI per CO ---
    qqi_scores = {}
    for c in cos:
        key = str(c["num"])
        t   = co_tally.get(key, {})
        n2, n5, n10 = t.get(2, 0), t.get(5, 0), t.get(10, 0)
        total = n2 + n5 + n10
        # Score components (0–100 each)
        adequacy    = min(100, total / max(1, 12 / max(len(cos), 1)) * 100)  # expect ~12 qs total / n_cos
        variety     = min(100, sum(1 for x in [n2, n5, n10] if x > 0) / 3 * 100)
        mark_balance = 100 - abs(n2 - n5) * 5 - abs(n5 - n10) * 5
        mark_balance = max(0, mark_balance)
        qqi_scores[f"CO{key}"] = round((adequacy * 0.4 + variety * 0.35 + mark_balance * 0.25))
    overall_qqi = round(sum(qqi_scores.values()) / max(len(qqi_scores), 1))

    return {
        "covered": sorted(covered),
        "uncovered": sorted(uncovered),
        "coverage_pct": coverage_pct,
        "total_2": total_2,
        "total_5": total_5,
        "total_10": total_10,
        "total_assign": total_assign,
        "total_quiz": total_quiz,
        "total_exam": total_exam,
        "diff_dist": diff_dist,
        "co_marks": co_marks,
        "total_marks": total_marks,
        "scenario_count": scenario_count,
        "direct_count": direct_count,
        "unclassified": unclassified,
        "total_analyzed": total_analyzed,
        "scenario_pct": scenario_pct,
        "qqi_scores": qqi_scores,
        "overall_qqi": overall_qqi,
    }


# ── Build sample question paper text ─────────────────────────────────────────

def build_sample_paper_text(qb_data: dict, code: str, title: str) -> list:
    """Return a list of (indent_level, text) tuples for the sample exam paper."""
    from generate_qpaper import _flat_list

    lines = []
    def add(text="", bold=False, indent=0):
        lines.append((indent, text, bold))

    add(f"{code} — {title}", bold=True)
    add("INTERNAL ASSESSMENT EXAMINATION (SAMPLE)", bold=True)
    add(f"Duration: 3 Hours   |   Maximum Marks: 50")
    add()
    add("Instructions:", bold=True)
    add("• Part A: Answer all questions                    (5 × 2 = 10 marks)", indent=1)
    add("• Part B: Answer any 2 out of 3 questions         (2 × 5 = 10 marks)", indent=1)
    add("• Part C: Answer any 1 out of 2 questions         (1 × 10 = 10 marks)", indent=1)
    add()
    add("-" * 70)
    add()
    add("PART A — Short Answer Questions (2 marks each)", bold=True)
    add()

    sel_2 = (_flat_list(qb_data["units"], "exam", 2))[:5]
    for i, (unit, q) in enumerate(sel_2, 1):
        co_tag = f"  [{q.get('co', '')}]" if q.get("co") else ""
        add(f"Q{i}.  {q.get('text', '')} {co_tag}", indent=1)
    add()
    add("-" * 70)
    add()
    add("PART B — Medium Answer Questions (5 marks each)", bold=True)
    add()
    sel_5 = (_flat_list(qb_data["units"], "exam", 5))[:3]
    for i, (unit, q) in enumerate(sel_5, 1):
        co_tag = f"  [{q.get('co', '')}]" if q.get("co") else ""
        add(f"Q{i}.  {q.get('text', '')} {co_tag}", indent=1)
    add()
    add("-" * 70)
    add()
    add("PART C — Long Answer Questions (10 marks each)", bold=True)
    add()
    sel_10 = (_flat_list(qb_data["units"], "exam", 10))[:2]
    for i, (unit, q) in enumerate(sel_10, 1):
        co_tag = f"  [{q.get('co', '')}]" if q.get("co") else ""
        add(f"Q{i}.  {q.get('text', '')} {co_tag}", indent=1)

    return lines


def _build_co_pct_rows(cos: list, co_tally: dict) -> list:
    """Return rows: (co, 2mk_str, 5mk_str, 10mk_str, assign_str, quiz_str, total_str).
    Each count cell shows 'N (X%)' where X% is share of that question type across all COs."""
    total_2    = sum(v.get(2,       0) for v in co_tally.values())
    total_5    = sum(v.get(5,       0) for v in co_tally.values())
    total_10   = sum(v.get(10,      0) for v in co_tally.values())
    total_asgn = sum(v.get("assign",0) for v in co_tally.values())
    total_quiz = sum(v.get("quiz",  0) for v in co_tally.values())

    def _fmt(n, tot):
        return f"{n} ({round(n/tot*100)}%)" if tot else str(n)

    rows = []
    for c in cos:
        key = str(c["num"])
        v   = co_tally.get(key, {})
        n2, n5, n10 = v.get(2,0), v.get(5,0), v.get(10,0)
        na, nq      = v.get("assign",0), v.get("quiz",0)
        rows.append((
            f"CO{key}",
            _fmt(n2,  total_2),
            _fmt(n5,  total_5),
            _fmt(n10, total_10),
            _fmt(na,  total_asgn),
            _fmt(nq,  total_quiz),
            str(n2 + n5 + n10 + na + nq),
        ))
    return rows


def _build_co_lab_pct_rows(cos: list, analytics: dict) -> list:
    """Return rows: (co, experiments, share%) for lab courses."""
    co_marks  = analytics.get("co_marks", {})
    total_exp = analytics.get("total_exp", analytics.get("total_exam", 0))
    rows = []
    for c in cos:
        key   = str(c["num"])
        n_exp = co_marks.get(key, 0)
        pct   = round(n_exp / total_exp * 100) if total_exp else 0
        rows.append((f"CO{key}", str(n_exp), f"{pct}%"))
    return rows


def build_sample_lab_paper_text(lab_data: dict, code: str, title: str) -> list:
    """Return a sample lab practical exam as (indent, text, bold) tuples."""
    from generate_qpaper import _flat_lab_list

    lines = []
    def add(text="", bold=False, indent=0):
        lines.append((indent, text, bold))

    add(f"{code} -- {title}", bold=True)
    add("LAB PRACTICAL EXAMINATION (SAMPLE)", bold=True)
    add("Duration: 3 Hours   |   Maximum Marks: 50")
    add()
    add("Instructions:", bold=True)
    add("* Perform the experiment and record your observations.", indent=1)
    add("* Write the aim, procedure, observations, and result in your lab record.", indent=1)
    add("* A brief viva will be conducted at the end of the session.", indent=1)
    add()
    add("-" * 70)
    add()
    add("PART A -- Practical Experiments", bold=True)
    add("(Attempt any ONE experiment from the list below)", indent=1)
    add()

    flat = _flat_lab_list(lab_data["units"])
    for i, (unit, exp) in enumerate(flat[:5], 1):
        co_tag = f"  [{exp.get('co', '')}]" if exp.get("co") else ""
        exp_title = exp.get("title") or exp.get("aim") or ""
        add(f"Exp {i}.  {exp_title}{co_tag}", indent=1)
    add()

    add("-" * 70)
    add()
    add("PART B -- Viva Voce Questions", bold=True)
    add("(Answer any FIVE questions — 2 marks each)", indent=1)
    add()

    viva_q = []
    for _, exp in flat:
        vivas = exp.get("viva") or []
        for vq in (vivas if isinstance(vivas, list) else []):
            text = vq.get("question", str(vq)) if isinstance(vq, dict) else str(vq)
            co   = exp.get("co", "")
            viva_q.append((text, co))
        if len(viva_q) >= 10:
            break

    if viva_q:
        for i, (text, co) in enumerate(viva_q[:10], 1):
            co_tag = f"  [{co}]" if co else ""
            add(f"Q{i}.  {text}{co_tag}", indent=1)
    else:
        add("(Viva questions will be asked based on the experiment performed.)", indent=1)

    return lines


# ── AI qualitative analysis call ─────────────────────────────────────────────

def get_ai_analysis(client, cos: list, co_tally: dict, bloom_summary: str,
                    code: str, title: str, analytics: dict) -> dict:
    """Single Claude call returning JSON for all qualitative report sections."""
    co_lines = "\n".join(f"  CO{c['num']}: {c['statement']}" for c in cos)
    tally_lines = "\n".join(
        f"  CO{k}: {v.get(2,0)}×2-mark, {v.get(5,0)}×5-mark, {v.get(10,0)}×10-mark"
        for k, v in co_tally.items()
    )

    prompt = f"""You are an NBA/NAAC accreditation expert for Indian engineering colleges.

Course: {title} ({code})
Course Outcomes:
{co_lines}

Bloom's Summary: {bloom_summary or "Not available"}

Question Bank Coverage per CO:
{tally_lines}

CO Coverage: {analytics["coverage_pct"]}% ({len(analytics["covered"])} of {len(analytics["covered"]) + len(analytics["uncovered"])} COs covered)
Total Questions: {analytics["total_2"]}×2-mark + {analytics["total_5"]}×5-mark + {analytics["total_10"]}×10-mark = {analytics["total_exam"]} exam questions
Scenario/Case-study questions detected: {analytics["scenario_count"]} ({analytics["scenario_pct"]}%)
Overall QQI (rule-based): {analytics["overall_qqi"]}/100

Provide a structured analysis in this EXACT JSON format (no markdown, no extra text):
{{
  "blooms_compliance": [
    {{"co": "CO1", "stated_level": "Apply", "qb_level": "Apply/Analyse mix", "rating": "Good", "remark": "..."}}
  ],
  "scenario_analysis": {{
    "assessment": "...(2-3 sentences on scenario coverage)",
    "recommendation": "...(1-2 sentences)"
  }},
  "qqi_interpretation": {{
    "overall": "...(2 sentences interpreting {analytics["overall_qqi"]}/100)",
    "strengths": ["...", "..."],
    "improvements": ["...", "..."]
  }},
  "obe_compliance": {{
    "co_statement_quality": "Excellent|Good|Satisfactory|Needs Improvement",
    "bloom_alignment": "Excellent|Good|Satisfactory|Needs Improvement",
    "co_coverage_status": "Excellent|Good|Satisfactory|Needs Improvement",
    "overall_obe_score": 85,
    "compliance_level": "Fully Compliant|Substantially Compliant|Partially Compliant",
    "strengths": ["...", "..."],
    "gaps": ["...", "..."],
    "recommendations": ["...", "..."]
  }},
  "accreditation_readiness": {{
    "overall_score": 82,
    "readiness_level": "Ready|Mostly Ready|Needs Work",
    "key_metrics": [
      {{"metric": "CO Formulation", "score": 90, "status": "Strong"}},
      {{"metric": "QB Coverage", "score": 75, "status": "Good"}},
      {{"metric": "Bloom's Alignment", "score": 80, "status": "Good"}},
      {{"metric": "Difficulty Balance", "score": 70, "status": "Adequate"}},
      {{"metric": "Scenario Integration", "score": 60, "status": "Needs Work"}}
    ],
    "action_items": ["...", "..."],
    "strengths": ["...", "..."]
  }}
}}"""

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Strip markdown fences
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        # Find the outermost JSON object bounds robustly
        start = raw.find('{')
        end   = raw.rfind('}')
        if start >= 0 and end > start:
            raw = raw[start:end + 1]
        return json.loads(raw)
    except Exception:
        return {}


# ── DOCX report builder ───────────────────────────────────────────────────────

def build_docx(
    cos: list,
    co_text: str,
    qb_data,            # parsed qb_data dict or None
    co_tally: dict,
    bloom_summary: str,
    analytics: dict,
    ai: dict,
    sample_paper,       # list of (indent, text, bold) tuples or []
    code: str,
    title: str,
    semester,
    output_path: str,
    is_lab: bool = False,
):
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()

    # Page margins
    for sec in doc.sections:
        sec.top_margin    = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin   = Inches(1.1)
        sec.right_margin  = Inches(1.1)

    # ── Helpers ──────────────────────────────────────────────────────────────
    INDIGO   = RGBColor(0x31, 0x2E, 0x81)
    TEAL     = RGBColor(0x06, 0x4E, 0x5B)
    GREEN    = RGBColor(0x06, 0x65, 0x28)
    AMBER    = RGBColor(0x78, 0x35, 0x00)
    RED_C    = RGBColor(0x7F, 0x1D, 0x1D)
    GRAY     = RGBColor(0x37, 0x41, 0x51)
    LIGHT_BG = RGBColor(0xEE, 0xEE, 0xFF)

    STATUS_COLOR = {
        "Excellent": GREEN, "Strong": GREEN, "Good": GREEN, "Ready": GREEN,
        "Satisfactory": AMBER, "Adequate": AMBER, "Mostly Ready": AMBER,
        "Needs Improvement": RED_C, "Needs Work": RED_C, "Poor": RED_C,
        "Fully Compliant": GREEN, "Substantially Compliant": AMBER,
        "Partially Compliant": RED_C,
    }

    def _add_heading(text, level=1, color=None):
        p = doc.add_heading(text, level=level)
        if color and p.runs:
            p.runs[0].font.color.rgb = color
        return p

    def _add_para(text="", bold=False, italic=False, color=None, size=10, space_after=4, indent=0):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        if indent:
            p.paragraph_format.left_indent = Inches(0.3 * indent)
        if text:
            run = p.add_run(text)
            run.bold   = bold
            run.italic = italic
            run.font.size = Pt(size)
            if color:
                run.font.color.rgb = color
        return p

    def _add_table(headers, rows, col_widths=None):
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        hdr = t.rows[0].cells
        for i, h in enumerate(headers):
            hdr[i].text = h
            for run in hdr[i].paragraphs[0].runs:
                run.bold = True
                run.font.size = Pt(9)
            tc = hdr[i]._tc
            tcp = tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"),   "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"),  "DDDDF0")
            tcp.append(shd)
        for row_data in rows:
            row = t.add_row().cells
            for i, val in enumerate(row_data):
                row[i].text = str(val)
                for run in row[i].paragraphs[0].runs:
                    run.font.size = Pt(9)
        if col_widths:
            for row in t.rows:
                for i, w in enumerate(col_widths):
                    row.cells[i].width = Inches(w)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        return t

    def _add_bar_chart(label_count_pairs, total, label_header="Category", unit_label=""):
        """Visual bar chart table using colored ■□ characters in Courier New."""
        t = doc.add_table(rows=1, cols=3)
        t.style = "Table Grid"
        hdr = t.rows[0].cells
        for i, h in enumerate([label_header, "Visual Distribution", "Count"]):
            hdr[i].text = h
            for run in hdr[i].paragraphs[0].runs:
                run.bold = True; run.font.size = Pt(9)
            tc = hdr[i]._tc
            tcp = tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), "DDDDF0")
            tcp.append(shd)
        for label, count in label_count_pairs:
            pct = round(count / total * 100) if total else 0
            filled_n = max(0, min(20, pct // 5))
            row = t.add_row().cells
            row[0].text = str(label)
            for run in row[0].paragraphs[0].runs:
                run.font.size = Pt(9)
            # Bar column: two colored runs
            p = row[1].paragraphs[0]
            if filled_n:
                r1 = p.add_run("■" * filled_n)
                r1.font.name = "Courier New"; r1.font.size = Pt(9)
                r1.font.color.rgb = RGBColor(0x4F, 0x46, 0xE5)   # indigo
            if filled_n < 20:
                r2 = p.add_run("□" * (20 - filled_n))
                r2.font.name = "Courier New"; r2.font.size = Pt(9)
                r2.font.color.rgb = RGBColor(0xC4, 0xB5, 0xFD)   # light lavender
            pct_run = p.add_run(f"  {pct}%")
            pct_run.font.size = Pt(8.5)
            pct_run.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)
            count_str = f"{count}{unit_label}"
            row[2].text = count_str
            for run in row[2].paragraphs[0].runs:
                run.font.size = Pt(9)
        for row in t.rows:
            row.cells[0].width = Inches(2.1)
            row.cells[1].width = Inches(3.4)
            row.cells[2].width = Inches(0.8)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def _badge(p, text, color):
        run = p.add_run(f"  {text}  ")
        run.bold = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = color

    def _section_divider(num, label):
        _add_heading(f"Section {num}: {label}", level=1, color=INDIGO)

    # ── Cover page ───────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(36)
    r = p.add_run("MyOBE — Module 1 Comprehensive Report")
    r.bold = True; r.font.size = Pt(18); r.font.color.rgb = INDIGO

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("AI-Powered Question Paper System")
    r2.italic = True; r2.font.size = Pt(12); r2.font.color.rgb = GRAY

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    meta = [
        ("Course Code",  code),
        ("Course Title", title),
        ("Semester",     str(semester) if semester else "—"),
        ("Generated on", datetime.date.today().strftime("%d %B %Y")),
    ]
    mt = doc.add_table(rows=len(meta), cols=2)
    mt.style = "Table Grid"
    for i, (k, v) in enumerate(meta):
        mt.rows[i].cells[0].text = k
        mt.rows[i].cells[1].text = v
        for run in mt.rows[i].cells[0].paragraphs[0].runs:
            run.bold = True; run.font.size = Pt(10)
        for run in mt.rows[i].cells[1].paragraphs[0].runs:
            run.font.size = Pt(10)
    for row in mt.rows:
        row.cells[0].width = Inches(2.2)
        row.cells[1].width = Inches(4.1)

    doc.add_page_break()

    # ── Executive Summary ────────────────────────────────────────────────────
    _add_heading("Executive Summary", level=1, color=INDIGO)
    n_cos   = len(cos)
    n_total = analytics["total_exam"]
    cov     = analytics["coverage_pct"]
    qqi     = analytics["overall_qqi"]
    acc     = ai.get("accreditation_readiness", {}).get("overall_score", "—")

    if is_lab:
        qb_desc = (
            f"The Lab Question Bank comprises {n_total} experiment(s) "
            f"covering {cov}% of the defined COs. "
        )
    else:
        qb_desc = (
            f"The Intelligent Question Bank comprises {n_total} examination questions "
            f"(2-mark, 5-mark, and 10-mark) covering {cov}% of the defined COs. "
        )
    _add_para(
        f"This report presents the complete Module 1 output for {title} ({code}). "
        f"A total of {n_cos} Course Outcomes were generated and mapped to Bloom's taxonomy. "
        + qb_desc +
        f"The overall Question Quality Index (QQI) is {qqi}/100, and the "
        f"Accreditation Readiness Score is {acc}/100.",
        size=10
    )

    key_stats = [
        ("Course Outcomes Generated", str(n_cos)),
        ("Total Exam Questions",      str(n_total)),
        ("Assignments in QB",         str(analytics["total_assign"])),
        ("Quiz Questions in QB",      str(analytics["total_quiz"])),
        ("CO Coverage",               f"{cov}%"),
        ("Question Quality Index",    f"{qqi}/100"),
        ("Accreditation Score",       f"{acc}/100"),
    ]
    _add_table(["Metric", "Value"], key_stats, col_widths=[3.5, 2.8])

    doc.add_page_break()

    # ── Section 1: Automatic CO Generation ──────────────────────────────────
    _section_divider(1, "Automatic CO Generation")
    _add_heading("Course Outcome Statements", level=2, color=TEAL)

    co_rows = []
    for c in cos:
        stmt = c["statement"]
        level = _detect_bloom(stmt)
        co_rows.append((f"CO{c['num']}", stmt, level))

    _add_table(["CO", "Statement", "Bloom's Level"], co_rows,
               col_widths=[0.6, 4.5, 1.2])

    # Always show Bloom's distribution — compute from CO statements when
    # bloom_summary string is empty (e.g. AIO flow without full CO text)
    _add_heading("Bloom's Taxonomy Distribution", level=2, color=TEAL)
    if bloom_summary:
        for line in bloom_summary.strip().split("\n"):
            if line.strip():
                _add_para(line.strip(), size=9.5)
        _add_para()
    bloom_counts: dict = {}
    for c in cos:
        lvl = _detect_bloom(c["statement"])
        bloom_counts[lvl] = bloom_counts.get(lvl, 0) + 1
    ORDER = ["Remember", "Understand", "Apply", "Analyse", "Evaluate", "Create"]
    bloom_dist_rows = [
        (lvl, str(bloom_counts.get(lvl, 0)),
         f"{round(bloom_counts.get(lvl, 0) / max(len(cos), 1) * 100, 1)}%")
        for lvl in ORDER if bloom_counts.get(lvl, 0) > 0
    ]
    if bloom_dist_rows:
        _add_table(["Bloom's Level", "CO Count", "Share"], bloom_dist_rows,
                   col_widths=[1.8, 1.1, 1.0])

    doc.add_page_break()

    # ── Section 2: Question Bank Creation ────────────────────────────────────
    _section_divider(2, "Lab Question Bank Creation" if is_lab else "Intelligent Question Bank Creation")

    if is_lab:
        total_exp = analytics.get("total_exp", analytics["total_exam"])
        qb_stats  = [
            ("Lab Experiments", str(total_exp)),
            ("Total Lab Work",  str(total_exp)),
        ]
        _add_table(["Category", "Count"], qb_stats, col_widths=[3.5, 2.8])
        _add_heading("CO-wise Experiment Distribution", level=2, color=TEAL)
        _add_para("Count and share (%) of experiments allocated to each CO.", italic=True, size=9)
        lab_pct_rows = _build_co_lab_pct_rows(cos, analytics)
        if lab_pct_rows:
            _add_table(["CO", "Experiments", "Share (%)"],
                       lab_pct_rows, col_widths=[0.8, 1.2, 1.0])
    else:
        qb_stats = [
            ("2-Mark Questions",    str(analytics["total_2"])),
            ("5-Mark Questions",    str(analytics["total_5"])),
            ("10-Mark Questions",   str(analytics["total_10"])),
            ("Assignment Tasks",    str(analytics["total_assign"])),
            ("Quiz Questions",      str(analytics["total_quiz"])),
            ("Total Exam Questions", str(analytics["total_exam"])),
        ]
        _add_table(["Category", "Count"], qb_stats, col_widths=[3.5, 2.8])
        _add_heading("CO-wise Question Distribution", level=2, color=TEAL)
        _add_para("Count and share (%) of each question type allocated to each CO.", italic=True, size=9)
        co_pct_rows = _build_co_pct_rows(cos, co_tally)
        if co_pct_rows:
            _add_table(
                ["CO", "2-Mk (%)", "5-Mk (%)", "10-Mk (%)", "Assign (%)", "Quiz (%)", "Total"],
                co_pct_rows,
                col_widths=[0.55, 0.85, 0.85, 0.85, 0.82, 0.73, 0.6]
            )

    doc.add_page_break()

    # ── Section 3: Sample Paper ───────────────────────────────────────────────
    _section_divider(3, "Lab Practical Examination (Sample)" if is_lab
                     else "Smart Question Paper / Assignment Generation")

    if sample_paper:
        for indent, text, bold in sample_paper:
            if not text:
                doc.add_paragraph()
                continue
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(3)
            if indent:
                p.paragraph_format.left_indent = Inches(0.35 * indent)
            run = p.add_run(text)
            run.bold = bold
            run.font.size = Pt(9.5)
    else:
        _add_para("Sample paper could not be generated — Question Bank is empty.", italic=True)

    doc.add_page_break()

    # ── Section 4: Bloom's Taxonomy Compliance Check ─────────────────────────
    _section_divider(4, "Bloom's Taxonomy Compliance Check")

    blooms_rows = []
    for entry in ai.get("blooms_compliance", []):
        rating = entry.get("rating", "—")
        blooms_rows.append((
            entry.get("co", ""),
            entry.get("stated_level", ""),
            entry.get("qb_level", ""),
            rating,
            entry.get("remark", ""),
        ))

    if blooms_rows:
        _add_table(["CO", "Stated Level", "QB Level Coverage", "Rating", "Remark"],
                   blooms_rows, col_widths=[0.6, 1.0, 1.3, 0.9, 2.5])
    else:
        _add_para("Bloom's compliance data not available.", italic=True)

    doc.add_page_break()

    # ── Section 5: CO Coverage Verification ─────────────────────────────────
    _section_divider(5, "CO Coverage Verification")

    cov_rows = []
    for c in cos:
        key = str(c["num"])
        t   = co_tally.get(key, {})
        total_q = t.get(2, 0) + t.get(5, 0) + t.get(10, 0)
        status  = "Covered" if total_q > 0 else "Not Covered"
        cov_rows.append((f"CO{key}", c["statement"], str(total_q), status))

    _add_table(["CO", "Statement", "Questions", "Status"],
               cov_rows, col_widths=[0.6, 3.7, 0.9, 1.1])

    _add_para(f"Overall Coverage: {cov}%  |  Covered: {len(analytics['covered'])}  |  "
              f"Not Covered: {len(analytics['uncovered'])}", bold=True, size=9.5)

    doc.add_page_break()

    # ── Section 6: Difficulty Level Analysis ────────────────────────────────
    _section_divider(6, "Difficulty Level Analysis")

    diff_rows = []
    total_q = analytics["total_exam"] or 1
    for label, count in analytics["diff_dist"].items():
        pct = round(count / total_q * 100, 1)
        diff_rows.append((label, str(count), f"{pct}%"))

    _add_table(["Difficulty Level", "Question Count", "Percentage"],
               diff_rows, col_widths=[2.5, 1.8, 1.5])

    _add_heading("Distribution Bar", level=2, color=TEAL)
    _add_bar_chart(list(analytics["diff_dist"].items()), total_q,
                   label_header="Difficulty Level", unit_label=" questions")

    doc.add_page_break()

    # ── Section 7: Scenario & Case Study Analysis ────────────────────────────
    _section_divider(7, "Scenario & Case Study Analysis")

    sc = analytics["scenario_count"]
    dc = analytics["direct_count"]
    uc = analytics.get("unclassified", 0)
    ta = analytics.get("total_analyzed", sc + dc + uc) or 1

    scenario_stats = [
        ("Scenario / Case Study questions", str(sc)),
        ("Direct / Factual questions",      str(dc)),
        ("Other / Unclassified",            str(uc)),
        ("Total Questions Analysed",        str(ta)),
        ("Scenario Coverage %",             f"{analytics['scenario_pct']}%"),
    ]
    _add_table(["Category", "Count"], scenario_stats, col_widths=[3.5, 2.8])

    sc_ai = ai.get("scenario_analysis", {})
    if sc_ai.get("assessment"):
        _add_heading("Assessment", level=2, color=TEAL)
        _add_para(sc_ai["assessment"], size=9.5)
    if sc_ai.get("recommendation"):
        _add_heading("Recommendation", level=2, color=TEAL)
        _add_para(sc_ai["recommendation"], size=9.5)

    doc.add_page_break()

    # ── Section 8: Question Quality Index (QQI) ──────────────────────────────
    _section_divider(8, "Question Quality Index (QQI)")

    qqi_rows = [(co, f"{score}/100") for co, score in analytics["qqi_scores"].items()]
    qqi_rows.append(("Overall QQI", f"{analytics['overall_qqi']}/100"))
    _add_table(["CO", "QQI Score"], qqi_rows, col_widths=[1.5, 1.5])

    qqi_ai = ai.get("qqi_interpretation", {})
    if qqi_ai.get("overall"):
        _add_para(qqi_ai["overall"], size=9.5)
    if qqi_ai.get("strengths"):
        _add_heading("Strengths", level=2, color=GREEN)
        for s in qqi_ai["strengths"]:
            _add_para(f"• {s}", size=9.5, indent=1)
    if qqi_ai.get("improvements"):
        _add_heading("Areas for Improvement", level=2, color=AMBER)
        for s in qqi_ai["improvements"]:
            _add_para(f"• {s}", size=9.5, indent=1)

    doc.add_page_break()

    # ── Section 9: CO-wise Marks Distribution ───────────────────────────────
    _section_divider(9, "CO-wise Marks Distribution")

    marks_rows = []
    for c in cos:
        key   = str(c["num"])
        marks = analytics["co_marks"].get(key, 0)
        pct   = round(marks / analytics["total_marks"] * 100, 1)
        marks_rows.append((f"CO{key}", str(marks), f"{pct}%"))

    _add_table(["CO", "Total Marks in QB", "Share (%)"],
               marks_rows, col_widths=[0.9, 2.2, 1.5])

    _add_heading("Distribution Bar", level=2, color=TEAL)
    marks_pairs = [(f"CO{c['num']}", analytics["co_marks"].get(str(c["num"]), 0)) for c in cos]
    _add_bar_chart(marks_pairs, analytics["total_marks"],
                   label_header="CO", unit_label=" marks")

    doc.add_page_break()

    # ── Section 10: OBE/NBA/NAAC/NEP Compliance Report ──────────────────────
    _section_divider(10, "OBE / NBA / NAAC / NEP Compliance Report")

    obe = ai.get("obe_compliance", {})
    obe_rows = [
        ("CO Statement Quality",  obe.get("co_statement_quality", "—")),
        ("Bloom's Alignment",     obe.get("bloom_alignment", "—")),
        ("CO Coverage Status",    obe.get("co_coverage_status", "—")),
        ("Overall OBE Score",     f"{obe.get('overall_obe_score', '—')}/100"),
        ("Compliance Level",      obe.get("compliance_level", "—")),
    ]
    _add_table(["Parameter", "Status"], obe_rows, col_widths=[3.0, 3.3])

    if obe.get("strengths"):
        _add_heading("Strengths", level=2, color=GREEN)
        for s in obe["strengths"]:
            _add_para(f"• {s}", size=9.5, indent=1)
    if obe.get("gaps"):
        _add_heading("Compliance Gaps", level=2, color=AMBER)
        for s in obe["gaps"]:
            _add_para(f"• {s}", size=9.5, indent=1)
    if obe.get("recommendations"):
        _add_heading("Recommendations", level=2, color=TEAL)
        for s in obe["recommendations"]:
            _add_para(f"• {s}", size=9.5, indent=1)

    doc.add_page_break()

    # ── Section 11: Accreditation Readiness Dashboard ───────────────────────
    _section_divider(11, "Accreditation Readiness Dashboard")

    acc_data = ai.get("accreditation_readiness", {})
    overall  = acc_data.get("overall_score", analytics["overall_qqi"])
    level    = acc_data.get("readiness_level", "Needs Work")

    _add_para(f"Overall Accreditation Readiness Score: {overall}/100  —  {level}",
              bold=True, size=12, color=STATUS_COLOR.get(level, GRAY))
    doc.add_paragraph()

    if acc_data.get("key_metrics"):
        _add_heading("Key Metrics", level=2, color=TEAL)
        metric_rows = [
            (m.get("metric", ""), f"{m.get('score', '—')}/100", m.get("status", "—"))
            for m in acc_data["key_metrics"]
        ]
        _add_table(["Metric", "Score", "Status"], metric_rows, col_widths=[2.8, 1.3, 1.5])

    if acc_data.get("strengths"):
        _add_heading("Strengths", level=2, color=GREEN)
        for s in acc_data["strengths"]:
            _add_para(f"• {s}", size=9.5, indent=1)

    if acc_data.get("action_items"):
        _add_heading("Action Items", level=2, color=AMBER)
        for s in acc_data["action_items"]:
            _add_para(f"• {s}", size=9.5, indent=1)

    _add_para()
    _add_para("─" * 80, size=8, color=GRAY)
    _add_para(
        f"Report generated by MyOBE on {datetime.date.today().strftime('%d %B %Y')}. "
        "This report is intended for internal academic and accreditation purposes.",
        italic=True, size=8, color=GRAY
    )

    doc.save(output_path)


# ── Plain-text report builder ─────────────────────────────────────────────────

def build_txt(
    cos, co_text, qb_data, co_tally, bloom_summary, analytics, ai,
    sample_paper, code, title, semester, output_path, is_lab=False,
):
    SEP  = "=" * 72
    SEP2 = "-" * 72
    date = datetime.date.today().strftime("%d %B %Y")

    def _sec(n, label):
        lines.append("")
        lines.append(SEP)
        lines.append(f"SECTION {n}: {label.upper()}")
        lines.append(SEP)

    def _sub(label):
        lines.append("")
        lines.append(label)
        lines.append(SEP2)

    def _tbl(headers, rows, widths=None):
        if not widths:
            widths = [max(len(h), max((len(str(r[i])) for r in rows), default=0))
                      for i, h in enumerate(headers)]
        fmt = "  ".join(f"{{:<{w}}}" for w in widths)
        lines.append(fmt.format(*headers))
        lines.append("  ".join("-" * w for w in widths))
        for row in rows:
            lines.append(fmt.format(*[str(v)[:w] for v, w in zip(row, widths)]))

    lines = []
    lines.append("MYOBE — MODULE 1 COMPREHENSIVE REPORT")
    lines.append("AI-Powered Question Paper System")
    lines.append(SEP)
    lines.append(f"Course Code  : {code}")
    lines.append(f"Course Title : {title}")
    lines.append(f"Semester     : {semester or '—'}")
    lines.append(f"Generated on : {date}")
    lines.append("")

    # Executive Summary
    lines.append(SEP)
    lines.append("EXECUTIVE SUMMARY")
    lines.append(SEP)
    acc = ai.get("accreditation_readiness", {}).get("overall_score", "—")
    lines.append(f"COs Generated          : {len(cos)}")
    lines.append(f"Total Exam Questions   : {analytics['total_exam']}")
    lines.append(f"Assignments in QB      : {analytics['total_assign']}")
    lines.append(f"Quiz Questions in QB   : {analytics['total_quiz']}")
    lines.append(f"CO Coverage            : {analytics['coverage_pct']}%")
    lines.append(f"Question Quality Index : {analytics['overall_qqi']}/100")
    lines.append(f"Accreditation Score    : {acc}/100")

    # Section 1: CO Generation
    _sec(1, "Automatic CO Generation")
    co_rows = [(f"CO{c['num']}", _detect_bloom(c["statement"]), c["statement"]) for c in cos]
    _tbl(["CO", "Bloom's", "Statement"], co_rows, [5, 10, 54])
    if bloom_summary:
        _sub("Bloom's Taxonomy Summary")
        lines.append(bloom_summary.strip())

    # Section 2: Question Bank
    _sec(2, "Lab Question Bank Creation" if is_lab else "Intelligent Question Bank Creation")
    if is_lab:
        total_exp = analytics.get("total_exp", analytics["total_exam"])
        _tbl(["Category", "Count"], [
            ("Lab Experiments", total_exp),
            ("Total Lab Work",  total_exp),
        ], [22, 8])
        _sub("CO-wise Experiment Distribution (count and % share)")
        lab_pct_rows = _build_co_lab_pct_rows(cos, analytics)
        _tbl(["CO", "Experiments", "Share (%)"], lab_pct_rows, [5, 12, 10])
    else:
        _tbl(["Category", "Count"], [
            ("2-Mark Questions",    analytics["total_2"]),
            ("5-Mark Questions",    analytics["total_5"]),
            ("10-Mark Questions",   analytics["total_10"]),
            ("Assignment Tasks",    analytics["total_assign"]),
            ("Quiz Questions",      analytics["total_quiz"]),
            ("Total Exam Questions",analytics["total_exam"]),
        ], [22, 8])
        _sub("CO-wise Question Distribution (count and % share of each type)")
        co_pct_rows = _build_co_pct_rows(cos, co_tally)
        _tbl(["CO", "2-Mk(%)", "5-Mk(%)", "10-Mk(%)", "Asgn(%)", "Quiz(%)", "Total"],
             co_pct_rows, [5, 10, 10, 10, 10, 10, 7])

    # Section 3: Sample Paper
    _sec(3, "Lab Practical Examination (Sample)" if is_lab
         else "Smart Question Paper / Assignment Generation")
    if sample_paper:
        for indent, text, bold in sample_paper:
            prefix = "  " * indent
            lines.append(prefix + text)
    else:
        lines.append("Sample paper not available.")

    # Section 4: Bloom's Compliance
    _sec(4, "Bloom's Taxonomy Compliance Check")
    bc = ai.get("blooms_compliance", [])
    if bc:
        _tbl(["CO", "Stated Level", "QB Level", "Rating", "Remark"],
             [(e.get("co",""), e.get("stated_level",""), e.get("qb_level",""),
               e.get("rating",""), e.get("remark","")[:35]) for e in bc],
             [5, 13, 18, 11, 35])
    else:
        lines.append("AI analysis not available.")

    # Section 5: CO Coverage
    _sec(5, "CO Coverage Verification")
    cov_rows = []
    for c in cos:
        key = str(c["num"])
        t   = co_tally.get(key, {})
        total_q = t.get(2,0) + t.get(5,0) + t.get(10,0)
        cov_rows.append((f"CO{key}", c["statement"], str(total_q),
                         "Covered" if total_q > 0 else "NOT COVERED"))
    _tbl(["CO", "Statement", "Questions", "Status"], cov_rows, [5, 55, 10, 12])
    lines.append(f"\nOverall Coverage: {analytics['coverage_pct']}%  |  "
                 f"Covered: {len(analytics['covered'])}  |  "
                 f"Not Covered: {len(analytics['uncovered'])}")

    # Section 6: Difficulty
    _sec(6, "Difficulty Level Analysis")
    total_q = analytics["total_exam"] or 1
    diff_rows = [(lbl, count, f"{round(count/total_q*100,1)}%")
                 for lbl, count in analytics["diff_dist"].items()]
    _tbl(["Level", "Count", "Pct"], diff_rows, [22, 7, 7])
    lines.append("")
    for lbl, count in analytics["diff_dist"].items():
        pct = round(count / total_q * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        lines.append(f"  {lbl:<20}  {bar}  {count}")

    # Section 7: Scenario Analysis
    _sec(7, "Scenario & Case Study Analysis")
    ta = analytics.get("total_analyzed", analytics["scenario_count"] + analytics["direct_count"]) or 1
    lines.append(f"Scenario / Case Study questions : {analytics['scenario_count']}")
    lines.append(f"Direct / Factual questions      : {analytics['direct_count']}")
    lines.append(f"Other / Unclassified            : {analytics.get('unclassified', 0)}")
    lines.append(f"Total Questions Analysed        : {ta}")
    lines.append(f"Scenario Coverage               : {analytics['scenario_pct']}%")
    sc_ai = ai.get("scenario_analysis", {})
    if sc_ai.get("assessment"):
        lines.append("")
        lines.append("Assessment:")
        lines.append(sc_ai["assessment"])
    if sc_ai.get("recommendation"):
        lines.append("")
        lines.append("Recommendation:")
        lines.append(sc_ai["recommendation"])

    # Section 8: QQI
    _sec(8, "Question Quality Index (QQI)")
    qqi_rows = [(co, f"{score}/100") for co, score in analytics["qqi_scores"].items()]
    qqi_rows.append(("Overall QQI", f"{analytics['overall_qqi']}/100"))
    _tbl(["CO", "QQI Score"], qqi_rows, [12, 10])
    qqi_ai = ai.get("qqi_interpretation", {})
    if qqi_ai.get("overall"):
        lines.append("\n" + qqi_ai["overall"])
    for label, key in [("Strengths", "strengths"), ("Improvements", "improvements")]:
        items = qqi_ai.get(key, [])
        if items:
            lines.append(f"\n{label}:")
            for s in items:
                lines.append(f"  • {s}")

    # Section 9: CO-wise Marks
    _sec(9, "CO-wise Marks Distribution")
    marks_rows = [(f"CO{c['num']}", analytics["co_marks"].get(str(c["num"]),0),
                   f"{round(analytics['co_marks'].get(str(c['num']),0)/analytics['total_marks']*100,1)}%")
                  for c in cos]
    _tbl(["CO", "Marks in QB", "Share"], marks_rows, [5, 12, 8])
    lines.append("")
    for c in cos:
        key   = str(c["num"])
        marks = analytics["co_marks"].get(key, 0)
        pct   = round(marks / analytics["total_marks"] * 100)
        bar   = "█" * (pct // 5) + "░" * (20 - pct // 5)
        lines.append(f"  CO{key:<4}  {bar}  {marks} marks ({pct}%)")

    # Section 10: OBE Compliance
    _sec(10, "OBE / NBA / NAAC / NEP Compliance Report")
    obe = ai.get("obe_compliance", {})
    if obe:
        lines.append(f"CO Statement Quality  : {obe.get('co_statement_quality','—')}")
        lines.append(f"Bloom's Alignment     : {obe.get('bloom_alignment','—')}")
        lines.append(f"CO Coverage Status    : {obe.get('co_coverage_status','—')}")
        lines.append(f"Overall OBE Score     : {obe.get('overall_obe_score','—')}/100")
        lines.append(f"Compliance Level      : {obe.get('compliance_level','—')}")
        for label, key in [("Strengths","strengths"),("Gaps","gaps"),("Recommendations","recommendations")]:
            items = obe.get(key, [])
            if items:
                lines.append(f"\n{label}:")
                for s in items:
                    lines.append(f"  • {s}")
    else:
        lines.append("OBE analysis not available.")

    # Section 11: Accreditation Readiness
    _sec(11, "Accreditation Readiness Dashboard")
    acc_data = ai.get("accreditation_readiness", {})
    overall  = acc_data.get("overall_score", analytics["overall_qqi"])
    level    = acc_data.get("readiness_level", "Needs Work")
    lines.append(f"Overall Score    : {overall}/100")
    lines.append(f"Readiness Level  : {level}")
    km = acc_data.get("key_metrics", [])
    if km:
        lines.append("")
        _tbl(["Metric", "Score", "Status"],
             [(m.get("metric",""), f"{m.get('score','—')}/100", m.get("status","")) for m in km],
             [28, 10, 14])
    for label, key in [("Strengths","strengths"),("Action Items","action_items")]:
        items = acc_data.get(key, [])
        if items:
            lines.append(f"\n{label}:")
            for s in items:
                lines.append(f"  • {s}")

    lines.append("")
    lines.append(SEP)
    lines.append(f"Report generated by MyOBE on {date}.")
    lines.append("This report is intended for internal academic and accreditation purposes.")
    lines.append(SEP)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── PDF report builder ────────────────────────────────────────────────────────

def build_pdf(
    cos, co_text, qb_data, co_tally, bloom_summary, analytics, ai,
    sample_paper, code, title, semester, output_path, is_lab=False,
):
    from fpdf import FPDF, XPos, YPos

    def _s(v):
        return str(v).replace("—", " - ").replace("–", " - ").replace(
            "’", "'").replace("‘", "'").replace(
            "“", '"').replace("”", '"').replace(
            "•", "*").replace("█", "#").replace(
            "░", ".").encode("latin-1", "replace").decode("latin-1")

    date = datetime.date.today().strftime("%d %B %Y")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(15, 15, 15)
    PAGE_W = 180  # usable width in mm (A4 - 2*15)

    # ── helpers ────────────────────────────────────────────────────────────────
    def _heading1(text):
        if pdf.get_y() > pdf.h - 40:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(220, 220, 240)
        pdf.cell(0, 9, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(1)

    def _heading2(text):
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.cell(0, 7, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(0.5)

    def _body(text, indent=0):
        pdf.set_font("Helvetica", "", 9.5)
        if indent:
            pdf.set_x(pdf.l_margin + indent * 4)
        pdf.multi_cell(0, 5.5, _s(str(text)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _kv(key, val):
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(50, 6, _s(key + ":"))
        pdf.set_font("Helvetica", "", 9.5)
        pdf.cell(0, 6, _s(str(val)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _tbl(headers, rows, col_ws):
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_fill_color(210, 210, 235)
        for h, w in zip(headers, col_ws):
            pdf.cell(w, 7, _s(h), border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8.5)
        for row in rows:
            # check page break before each row
            if pdf.get_y() > pdf.h - 20:
                pdf.add_page()
            for val, w in zip(row, col_ws):
                pdf.cell(w, 6, _s(str(val))[:int(w*1.5)], border=1)
            pdf.ln()
        pdf.ln(2)

    def _bullets(items, indent=5):
        pdf.set_font("Helvetica", "", 9.5)
        for item in items:
            pdf.set_x(pdf.l_margin + indent)
            pdf.multi_cell(PAGE_W - indent, 5.5, _s("* " + str(item)),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _bar_row(label, pct, count):
        filled = int(pct / 5)
        bar = "#" * filled + "." * (20 - filled)
        pdf.set_font("Courier", "", 8.5)
        pdf.cell(0, 5, _s(f"  {label:<22} [{bar}] {count}"),
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Cover page ──────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_fill_color(49, 46, 129)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "MyOBE - Module 1 Comprehensive Report",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align="C")
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_fill_color(99, 102, 241)
    pdf.cell(0, 9, "AI-Powered Question Paper System",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
    for k, v in [("Course Code", code), ("Course Title", title),
                  ("Semester", str(semester) if semester else "-"),
                  ("Generated on", date)]:
        _kv(k, v)

    # Executive Summary
    pdf.ln(6)
    _heading1("EXECUTIVE SUMMARY")
    acc = ai.get("accreditation_readiness", {}).get("overall_score", "-")
    _tbl(
        ["Metric", "Value"],
        [
            ("COs Generated",          len(cos)),
            ("Total Exam Questions",    analytics["total_exam"]),
            ("Assignments in QB",       analytics["total_assign"]),
            ("Quiz Questions in QB",    analytics["total_quiz"]),
            ("CO Coverage",             f"{analytics['coverage_pct']}%"),
            ("Question Quality Index",  f"{analytics['overall_qqi']}/100"),
            ("Accreditation Score",     f"{acc}/100"),
        ],
        [110, 60],
    )

    # Section 1
    pdf.add_page()
    _heading1("SECTION 1: AUTOMATIC CO GENERATION")
    # Section 1 CO table — use multi-line rows so full statement is visible
    _heading2("Course Outcome Statements")
    COL_CO1  = 14
    COL_BL1  = 26
    COL_STMT1 = PAGE_W - COL_CO1 - COL_BL1
    LH1, PAD1 = 5.0, 1.5
    chars_per_line1 = max(1, int(COL_STMT1 / 2.0))

    def _co_hdr():
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_fill_color(210, 210, 235)
        for lbl, w in [("CO", COL_CO1), ("Bloom's Level", COL_BL1), ("Statement", COL_STMT1)]:
            pdf.cell(w, 7, lbl, border=1, fill=True)
        pdf.ln()

    _co_hdr()
    pdf.set_font("Helvetica", "", 8.5)
    for c in cos:
        stmt_safe = _s(c["statement"])
        stmt_lines = [stmt_safe[i:i+chars_per_line1]
                      for i in range(0, max(1, len(stmt_safe)), chars_per_line1)]
        row_h = max(7, len(stmt_lines) * LH1 + PAD1 * 2)
        if pdf.get_y() + row_h > pdf.h - 18:
            pdf.add_page(); _co_hdr(); pdf.set_font("Helvetica", "", 8.5)
        y0 = pdf.get_y(); x0 = pdf.l_margin
        pdf.rect(x0, y0, COL_CO1, row_h)
        pdf.rect(x0 + COL_CO1, y0, COL_BL1, row_h)
        pdf.rect(x0 + COL_CO1 + COL_BL1, y0, COL_STMT1, row_h)
        pdf.set_xy(x0 + PAD1, y0 + (row_h - LH1) / 2)
        pdf.cell(COL_CO1 - PAD1, LH1, _s(f"CO{c['num']}"), border=0)
        pdf.set_xy(x0 + COL_CO1 + PAD1, y0 + (row_h - LH1) / 2)
        pdf.cell(COL_BL1 - PAD1, LH1, _s(_detect_bloom(c["statement"])), border=0)
        for li, line in enumerate(stmt_lines):
            pdf.set_xy(x0 + COL_CO1 + COL_BL1 + PAD1, y0 + PAD1 + li * LH1)
            pdf.cell(COL_STMT1 - PAD1 * 2, LH1, line, border=0)
        pdf.set_y(y0 + row_h)
    pdf.ln(2)
    if bloom_summary:
        _heading2("Bloom's Taxonomy Summary")
        _body(bloom_summary.strip())

    # Section 2
    pdf.add_page()
    _heading1("SECTION 2: LAB QUESTION BANK CREATION" if is_lab
              else "SECTION 2: INTELLIGENT QUESTION BANK CREATION")
    if is_lab:
        total_exp = analytics.get("total_exp", analytics["total_exam"])
        _tbl(["Category", "Count"], [
            ("Lab Experiments", total_exp),
            ("Total Lab Work",  total_exp),
        ], [130, 40])
        _heading2("CO-wise Experiment Distribution")
        _body("Count and share (%) of experiments allocated to each CO.")
        lab_pct_rows = _build_co_lab_pct_rows(cos, analytics)
        _tbl(["CO", "Experiments", "Share (%)"], lab_pct_rows, [20, 40, 30])
    else:
        _tbl(["Category", "Count"], [
            ("2-Mark Questions",     analytics["total_2"]),
            ("5-Mark Questions",     analytics["total_5"]),
            ("10-Mark Questions",    analytics["total_10"]),
            ("Assignment Tasks",     analytics["total_assign"]),
            ("Quiz Questions",       analytics["total_quiz"]),
            ("Total Exam Questions", analytics["total_exam"]),
        ], [130, 40])
        _heading2("CO-wise Question Distribution")
        _body("Count and share (%) of each question type allocated to each CO.")
        co_pct_rows = _build_co_pct_rows(cos, co_tally)
        # Columns: CO(12) | 2-Mk%(26) | 5-Mk%(26) | 10-Mk%(26) | Assign%(26) | Quiz%(22) | Total(14) = 152mm
        _tbl(
            ["CO", "2-Mk (%)", "5-Mk (%)", "10-Mk (%)", "Assign (%)", "Quiz (%)", "Total"],
            co_pct_rows,
            [12, 26, 26, 26, 26, 22, 14]
        )

    # Section 3: Sample Paper
    pdf.add_page()
    _heading1("SECTION 3: LAB PRACTICAL EXAMINATION (SAMPLE)" if is_lab
              else "SECTION 3: SMART QUESTION PAPER (SAMPLE)")
    if sample_paper:
        for indent, text, bold in sample_paper:
            pdf.set_font("Helvetica", "B" if bold else "", 9)
            x_offset = indent * 5
            if x_offset:
                pdf.set_x(pdf.l_margin + x_offset)
            pdf.multi_cell(PAGE_W - x_offset, 5.5, _s(text),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        _body("Sample paper not available.")

    # Section 4: Bloom's Compliance — wider columns to avoid overflow
    pdf.add_page()
    _heading1("SECTION 4: BLOOM'S TAXONOMY COMPLIANCE CHECK")
    bc = ai.get("blooms_compliance", [])
    if bc:
        _tbl(["CO", "Stated Level", "QB Level Coverage", "Rating"],
             [(e.get("co",""), e.get("stated_level",""), e.get("qb_level",""),
               e.get("rating","")) for e in bc],
             [14, 38, 90, 38])
        for e in bc:
            if e.get("remark"):
                _body(f"{e.get('co','')}: {e['remark']}")
    else:
        _body("AI analysis not available.")

    # Section 5: CO Coverage — uses per-row multi_cell for full statement wrapping
    pdf.add_page()
    _heading1("SECTION 5: CO COVERAGE VERIFICATION")

    COL_CO   = 16
    COL_STMT = 105
    COL_Q    = 22
    COL_ST   = 37
    LH       = 5.5   # line height per text line
    PAD      = 1.5

    def _cov_header():
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_fill_color(210, 210, 235)
        for lbl, w in [("CO", COL_CO), ("Statement", COL_STMT),
                        ("Questions", COL_Q), ("Status", COL_ST)]:
            pdf.cell(w, 7, lbl, border=1, fill=True)
        pdf.ln()

    _cov_header()
    pdf.set_font("Helvetica", "", 8.5)
    for c in cos:
        key  = str(c["num"])
        t    = co_tally.get(key, {})
        tot  = t.get(2,0) + t.get(5,0) + t.get(10,0)
        stat = "Covered" if tot > 0 else "NOT COVERED"

        stmt_safe = _s(c["statement"])
        chars_per_line = max(1, int(COL_STMT / 2.1))
        stmt_lines = [stmt_safe[i:i+chars_per_line]
                      for i in range(0, max(1, len(stmt_safe)), chars_per_line)]
        row_h = max(7, len(stmt_lines) * LH + PAD * 2)

        if pdf.get_y() + row_h > pdf.h - 18:
            pdf.add_page(); _cov_header()
            pdf.set_font("Helvetica", "", 8.5)

        y0 = pdf.get_y(); x0 = pdf.l_margin

        pdf.rect(x0,              y0, COL_CO,   row_h)
        pdf.rect(x0 + COL_CO,     y0, COL_STMT, row_h)
        pdf.rect(x0 + COL_CO + COL_STMT,       y0, COL_Q, row_h)
        pdf.rect(x0 + COL_CO + COL_STMT + COL_Q, y0, COL_ST, row_h)

        # CO cell
        pdf.set_xy(x0 + PAD, y0 + (row_h - LH) / 2)
        pdf.cell(COL_CO - PAD, LH, _s(f"CO{key}"), border=0)

        # Statement cell — line by line
        for li, line in enumerate(stmt_lines):
            pdf.set_xy(x0 + COL_CO + PAD, y0 + PAD + li * LH)
            pdf.cell(COL_STMT - PAD * 2, LH, line, border=0)

        # Questions cell
        pdf.set_xy(x0 + COL_CO + COL_STMT + PAD, y0 + (row_h - LH) / 2)
        pdf.cell(COL_Q - PAD, LH, str(tot), border=0, align="C")

        # Status cell
        pdf.set_xy(x0 + COL_CO + COL_STMT + COL_Q + PAD, y0 + (row_h - LH) / 2)
        pdf.cell(COL_ST - PAD, LH, _s(stat), border=0)

        pdf.set_y(y0 + row_h)
    pdf.ln(2)
    _body(f"Overall Coverage: {analytics['coverage_pct']}%  |  "
          f"Covered: {len(analytics['covered'])}  |  Not Covered: {len(analytics['uncovered'])}")

    # Section 6: Difficulty
    pdf.add_page()
    _heading1("SECTION 6: DIFFICULTY LEVEL ANALYSIS")
    total_q = analytics["total_exam"] or 1
    _tbl(["Level", "Count", "Percentage"],
         [(lbl, cnt, f"{round(cnt/total_q*100,1)}%") for lbl, cnt in analytics["diff_dist"].items()],
         [60, 25, 25])
    _heading2("Distribution")
    for lbl, cnt in analytics["diff_dist"].items():
        _bar_row(lbl, round(cnt / total_q * 100), cnt)

    # Section 7: Scenario Analysis
    pdf.add_page()
    _heading1("SECTION 7: SCENARIO & CASE STUDY ANALYSIS")
    _tbl(["Category", "Count"], [
        ("Scenario / Case Study questions", analytics["scenario_count"]),
        ("Direct / Factual questions",      analytics["direct_count"]),
        ("Scenario Coverage %",             f"{analytics['scenario_pct']}%"),
    ], [120, 50])
    sc_ai = ai.get("scenario_analysis", {})
    if sc_ai.get("assessment"):
        _heading2("Assessment")
        _body(sc_ai["assessment"])
    if sc_ai.get("recommendation"):
        _heading2("Recommendation")
        _body(sc_ai["recommendation"])

    # Section 8: QQI
    pdf.add_page()
    _heading1("SECTION 8: QUESTION QUALITY INDEX (QQI)")
    qqi_rows = [(co, f"{score}/100") for co, score in analytics["qqi_scores"].items()]
    qqi_rows.append(("Overall QQI", f"{analytics['overall_qqi']}/100"))
    _tbl(["CO", "QQI Score"], qqi_rows, [40, 40])
    qqi_ai = ai.get("qqi_interpretation", {})
    if qqi_ai.get("overall"):
        _body(qqi_ai["overall"])
    if qqi_ai.get("strengths"):
        _heading2("Strengths")
        _bullets(qqi_ai["strengths"])
    if qqi_ai.get("improvements"):
        _heading2("Areas for Improvement")
        _bullets(qqi_ai["improvements"])

    # Section 9: CO Marks
    pdf.add_page()
    _heading1("SECTION 9: CO-WISE MARKS DISTRIBUTION")
    marks_rows = [(f"CO{c['num']}",
                   analytics["co_marks"].get(str(c["num"]), 0),
                   f"{round(analytics['co_marks'].get(str(c['num']),0)/analytics['total_marks']*100,1)}%")
                  for c in cos]
    _tbl(["CO", "Marks in QB", "Share"], marks_rows, [20, 40, 30])
    _heading2("Distribution")
    for c in cos:
        key   = str(c["num"])
        marks = analytics["co_marks"].get(key, 0)
        pct   = round(marks / analytics["total_marks"] * 100)
        _bar_row(f"CO{key}", pct, f"{marks} marks ({pct}%)")

    # Section 10: OBE Compliance
    pdf.add_page()
    _heading1("SECTION 10: OBE / NBA / NAAC / NEP COMPLIANCE REPORT")
    obe = ai.get("obe_compliance", {})
    if obe:
        _tbl(["Parameter", "Status"], [
            ("CO Statement Quality",  obe.get("co_statement_quality", "-")),
            ("Bloom's Alignment",     obe.get("bloom_alignment", "-")),
            ("CO Coverage Status",    obe.get("co_coverage_status", "-")),
            ("Overall OBE Score",     f"{obe.get('overall_obe_score','-')}/100"),
            ("Compliance Level",      obe.get("compliance_level", "-")),
        ], [90, 80])
        if obe.get("strengths"):
            _heading2("Strengths")
            _bullets(obe["strengths"])
        if obe.get("gaps"):
            _heading2("Compliance Gaps")
            _bullets(obe["gaps"])
        if obe.get("recommendations"):
            _heading2("Recommendations")
            _bullets(obe["recommendations"])
    else:
        _body("OBE analysis not available.")

    # Section 11: Accreditation Readiness
    pdf.add_page()
    _heading1("SECTION 11: ACCREDITATION READINESS DASHBOARD")
    acc_data = ai.get("accreditation_readiness", {})
    overall  = acc_data.get("overall_score", analytics["overall_qqi"])
    level    = acc_data.get("readiness_level", "Needs Work")
    _kv("Overall Score",   f"{overall}/100")
    _kv("Readiness Level", level)
    pdf.ln(2)
    km = acc_data.get("key_metrics", [])
    if km:
        _heading2("Key Metrics")
        _tbl(["Metric", "Score", "Status"],
             [(m.get("metric",""), f"{m.get('score','-')}/100", m.get("status","")) for m in km],
             [90, 30, 40])
    if acc_data.get("strengths"):
        _heading2("Strengths")
        _bullets(acc_data["strengths"])
    if acc_data.get("action_items"):
        _heading2("Action Items")
        _bullets(acc_data["action_items"])

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, _s(f"Report generated by MyOBE on {date}. For internal academic and accreditation use."),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(output_path)
