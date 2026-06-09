"""Module 4 Comprehensive Assessment Report Generator.

Builds a DOCX/PDF/TXT report covering all Module-4 deliverables:
  1.  Course Overview
  2.  CO-PO-PSO Mapping Table
  3.  CO Strength Summary (avg PO score per CO)
  4.  CO Attainment Analysis
  5.  PO Attainment Summary
  6.  Attainment Level Distribution
  7.  CO to SDG Contribution Analysis
  8.  PO to SDG Contribution Analysis
  9.  Composite SDG Index
 10.  NBA/NAAC Assessment Compliance Checklist
 11.  Assessment Readiness Dashboard
 12.  Action Taken Report
"""

import re
import datetime

try:
    import report_charts as _rc
except Exception:
    _rc = None


# ── Analytics ─────────────────────────────────────────────────────────────────

def compute_analytics(pomap_rows, coatt_data, poatt_data, sdgco_data, sdgpo_data):
    pomap  = pomap_rows  or []
    coatt  = coatt_data  or {}
    poatt  = poatt_data  or {}
    sdgco  = sdgco_data  or {}
    sdgpo  = sdgpo_data  or {}

    co_results  = coatt.get("coResults", [])
    po_results  = coatt.get("poResults", [])
    thresholds  = coatt.get("thresholds", {"t1": 70, "t2": 60, "t3": 50})

    # CO names from pomap or coatt
    co_names = [r.get("co", "") for r in pomap] or [r.get("co", "") for r in co_results]
    n_cos = len(co_names) or len(co_results)

    # PO keys from pomap
    po_keys = list(pomap[0].get("scores", {}).keys()) if pomap else [f"PO{i}" for i in range(1, 13)]
    n_pos   = len(po_keys)

    # Average PO score per CO (strength)
    co_strength = {}
    for row in pomap:
        scores = row.get("scores", {})
        vals   = [v for v in scores.values() if v is not None]
        co_strength[row.get("co", "")] = round(sum(vals) / len(vals), 2) if vals else 0

    # Average score per PO (column average)
    po_avg = {}
    for pk in po_keys:
        vals = [row.get("scores", {}).get(pk, 0) for row in pomap]
        po_avg[pk] = round(sum(vals) / len(vals), 2) if vals else 0

    # Attainment level distribution
    level_dist = {3: 0, 2: 0, 1: 0, 0: 0}
    for r in co_results:
        lv = int(r.get("level", 0))
        level_dist[lv] = level_dist.get(lv, 0) + 1

    # Mean CO attainment %
    pcts = [r.get("pct", 0) for r in co_results]
    mean_att_pct = round(sum(pcts) / len(pcts), 2) if pcts else 0

    # SDG CO
    target_sdg     = sdgco.get("targetSdg", "")
    sdgco_contrib  = sdgco.get("contributions", [])
    sdgco_total    = sdgco.get("total", 0)

    # SDG PO
    sdgpo_results  = sdgpo.get("results", [])
    sdgpo_composite = sdgpo.get("composite", 0)
    sdgs_covered   = [r.get("sdg", "") for r in sdgpo_results]

    # PO Attainment (dedicated tool)
    po_attainment   = poatt.get("po_attainment", [])
    po_att_summary  = poatt.get("summary", {})
    atr_rows        = [p for p in po_attainment if not p.get("target_met")]

    return dict(
        co_names=co_names,
        n_cos=n_cos,
        po_keys=po_keys,
        n_pos=n_pos,
        pomap_rows=pomap,
        co_strength=co_strength,
        po_avg=po_avg,
        co_results=co_results,
        po_results=po_results,
        thresholds=thresholds,
        level_dist=level_dist,
        mean_att_pct=mean_att_pct,
        target_sdg=target_sdg,
        sdgco_contrib=sdgco_contrib,
        sdgco_total=sdgco_total,
        sdgpo_results=sdgpo_results,
        sdgpo_composite=sdgpo_composite,
        sdgs_covered=sdgs_covered,
        po_attainment=po_attainment,
        po_att_summary=po_att_summary,
        atr_rows=atr_rows,
    )


# ── AI analysis ───────────────────────────────────────────────────────────────

def get_ai_analysis(client, all_data, analytics, code, title):
    co_lines   = "\n".join(f"  {r['co']}: {r['pct']:.1f}% (Level {r['level']})" for r in analytics["co_results"][:8])
    po_lines   = "\n".join(f"  {r['po']}: {r['attainment']}" for r in analytics["po_results"][:12])
    sdg_lines  = "\n".join(f"  {r['sdg']}: {r['contribution']:.1f}% ({r['interpretation']})" for r in analytics["sdgpo_results"][:5])
    target_sdg = analytics["target_sdg"]

    prompt = (
        f"You are an NBA/NAAC accreditation expert for Indian engineering colleges.\n\n"
        f"Course: {title} ({code})\n\n"
        f"CO Attainment (AI-estimated):\n{co_lines or '  Not available'}\n\n"
        f"PO Attainment:\n{po_lines or '  Not available'}\n\n"
        f"Target SDG (CO-level): {target_sdg or 'Not set'}\n\n"
        f"PO-SDG Contributions:\n{sdg_lines or '  Not available'}\n\n"
        "Provide a structured assessment in this exact JSON format:\n"
        "{\n"
        '  "attainment_quality": "2-sentence assessment of CO/PO attainment levels",\n'
        '  "mapping_strength": "1-sentence on CO-PO mapping robustness",\n'
        '  "sdg_integration": "1-sentence on SDG alignment quality",\n'
        '  "nba_compliance": "1-sentence NBA/NAAC compliance observation",\n'
        '  "recommendations": ["rec 1", "rec 2", "rec 3"],\n'
        '  "readiness_score": <integer 0-100 overall assessment readiness>\n'
        "}"
    )

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        import json as _json
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return _json.loads(raw.strip())
    except Exception:
        return {}


# ── Shared text builder ───────────────────────────────────────────────────────

def _build_txt(pomap_data, coatt_data, poatt_data, sdgco_data, sdgpo_data,
               analytics, ai, code, title, semester):
    a    = analytics
    now  = datetime.datetime.now().strftime("%d %b %Y")
    sem  = f"Semester {semester}  |  " if semester else ""
    lines = []

    def h1(t): lines.extend([t, "=" * len(t), ""])
    def h2(t): lines.extend([t, "-" * len(t), ""])
    def row(*cols): lines.append("  ".join(str(c) for c in cols))

    h1(f"MODULE 4 COMPREHENSIVE ASSESSMENT REPORT")
    lines.append(f"Course: {title} ({code})  |  {sem}Generated: {now}")
    lines.append("")

    h2("1. COURSE OVERVIEW")
    lines.append(f"  Course Outcomes   : {a['n_cos']}")
    lines.append(f"  Programme Outcomes: {a['n_pos']}")
    lines.append(f"  Mean CO Attainment: {a['mean_att_pct']}%")
    lines.append(f"  SDG Focus (CO)    : {a['target_sdg'] or 'N/A'}")
    lines.append(f"  SDG Coverage (PO) : {len(a['sdgs_covered'])} SDGs")
    lines.append("")

    h2("2. CO-PO MAPPING TABLE  (3=Strong  2=Moderate  1=Low  0=None)")
    if a["pomap_rows"]:
        pk = a["po_keys"]
        row("CO".ljust(8), *[k.ljust(4) for k in pk])
        lines.append("  " + "-" * (8 + 6 * len(pk)))
        for r in a["pomap_rows"]:
            sc = [str(r.get("scores", {}).get(k, 0)).ljust(4) for k in pk]
            row(r.get("co", "").ljust(8), *sc)
    else:
        lines.append("  No mapping data.")
    lines.append("")

    h2("3. CO STRENGTH SUMMARY")
    for co, avg in a["co_strength"].items():
        bar = "#" * int(avg / 3 * 20)
        lines.append(f"  {co:<8} avg={avg:.2f}  {bar}")
    lines.append("")

    h2("4. CO ATTAINMENT ANALYSIS")
    t = a["thresholds"]
    lines.append(f"  Thresholds: Level 3 >= {t['t1']}%  Level 2 >= {t['t2']}%  Level 1 >= {t['t3']}%")
    lines.append("")
    row("  CO".ljust(10), "Attainment%".ljust(14), "Level")
    lines.append("  " + "-" * 30)
    for r in a["co_results"]:
        row(f"  {r['co']}".ljust(10), f"{r['pct']:.2f}%".ljust(14), r["level"])
    lines.append(f"\n  Mean: {a['mean_att_pct']}%")
    lines.append("")

    h2("5. PO ATTAINMENT SUMMARY")
    if a["po_results"]:
        row("  " + "  ".join(f"{r['po']}".ljust(5) for r in a["po_results"]))
        row("  " + "  ".join(f"{r['attainment']:.2f}".ljust(5) for r in a["po_results"]))
    lines.append("")

    h2("5b. PO ATTAINMENT ANALYSIS  (NBA Method)")
    if a["po_attainment"]:
        pa_sum = a["po_att_summary"]
        lines.append(f"  Mean PO Attainment: {pa_sum.get('mean_pct', 0):.1f}%  |  "
                     f"POs Meeting Target: {pa_sum.get('pos_meeting_target', 0)}/{len(a['po_attainment'])}")
        lines.append("")
        row("  PO".ljust(8), "Name".ljust(34), "Att%".ljust(8), "Level", "Target")
        lines.append("  " + "-" * 62)
        for p in a["po_attainment"]:
            row(f"  {p['po']}".ljust(8), p["name"][:34].ljust(34),
                f"{p['pct']:.1f}%".ljust(8), str(p["level"]), "Met" if p["target_met"] else "Below")
    else:
        lines.append("  Run PO Attainment tool to see this section.")
    lines.append("")

    h2("6. ATTAINMENT LEVEL DISTRIBUTION")
    ld = a["level_dist"]
    for lv in [3, 2, 1, 0]:
        bar = "#" * ld.get(lv, 0)
        lines.append(f"  Level {lv}: {ld.get(lv, 0):>2} CO(s)  {bar}")
    lines.append("")

    h2("7. CO TO SDG CONTRIBUTION ANALYSIS")
    if a["sdgco_contrib"]:
        lines.append(f"  Target SDG: {a['target_sdg']}")
        row("  CO".ljust(10), "Score".ljust(8), "Share%")
        lines.append("  " + "-" * 28)
        for c in a["sdgco_contrib"]:
            row(f"  {c['co']}".ljust(10), str(c["score"]).ljust(8), f"{c['pct']:.1f}%")
        lines.append(f"\n  Total score: {a['sdgco_total']}")
    else:
        lines.append("  No CO-SDG data.")
    lines.append("")

    h2("8. PO TO SDG CONTRIBUTION ANALYSIS")
    if a["sdgpo_results"]:
        for r in a["sdgpo_results"]:
            lines.append(f"  {r['sdg']:<48}  {r['contribution']:.2f}%  ({r['interpretation']})")
    else:
        lines.append("  No PO-SDG data.")
    lines.append("")

    h2("9. COMPOSITE SDG INDEX")
    lines.append(f"  Composite SDG Index: {a['sdgpo_composite']:.2f}%")
    interp = ("Excellent" if a["sdgpo_composite"] >= 85 else
              "Strong"    if a["sdgpo_composite"] >= 70 else
              "Moderate"  if a["sdgpo_composite"] >= 50 else "Weak")
    lines.append(f"  Interpretation: {interp}")
    lines.append("")

    h2("10. NBA/NAAC ASSESSMENT COMPLIANCE CHECKLIST")
    has_pomap   = bool(a["pomap_rows"])
    has_coatt   = bool(a["co_results"])
    has_sdgco   = bool(a["sdgco_contrib"])
    has_sdgpo   = bool(a["sdgpo_results"])
    good_att    = a["mean_att_pct"] >= 60
    multi_sdg   = len(a["sdgs_covered"]) >= 2
    has_atr     = (not a["atr_rows"]) or all(p.get("atr", "").strip() for p in a["atr_rows"])
    checks = [
        ("CO-PO Mapping generated",                    has_pomap),
        ("CO Attainment calculated",                   has_coatt),
        ("CO-level SDG contribution mapped",           has_sdgco),
        ("PO-level SDG contribution mapped",           has_sdgpo),
        ("Mean CO attainment >= 60%",                  good_att),
        ("Multiple SDGs covered",                      multi_sdg),
        ("Action Taken Report documented",             has_atr),
    ]
    for label, ok in checks:
        lines.append(f"  {'[OK]' if ok else '[  ]'}  {label}")
    lines.append("")

    h2("11. ASSESSMENT READINESS DASHBOARD")
    if ai:
        lines.append(f"  Readiness Score: {ai.get('readiness_score', 'N/A')}/100")
        lines.append("")
        if ai.get("attainment_quality"):
            lines.append(f"  Attainment Quality: {ai['attainment_quality']}")
        if ai.get("mapping_strength"):
            lines.append(f"  Mapping Strength: {ai['mapping_strength']}")
        if ai.get("sdg_integration"):
            lines.append(f"  SDG Integration: {ai['sdg_integration']}")
        if ai.get("nba_compliance"):
            lines.append(f"  NBA/NAAC Compliance: {ai['nba_compliance']}")
        recs = ai.get("recommendations", [])
        if recs:
            lines.append("\n  Recommendations:")
            for i, r in enumerate(recs, 1):
                lines.append(f"  {i}. {r}")
    else:
        score = _rule_readiness(a)
        lines.append(f"  Readiness Score: {score}/100")
    lines.append("")

    h2("12. ACTION TAKEN REPORT")
    lines.append("  Corrective actions for Programme Outcomes below attainment target.")
    lines.append("")
    if not a["po_attainment"]:
        lines.append("  Run PO Attainment tool to generate this section.")
    elif not a["atr_rows"]:
        lines.append("  All Programme Outcomes met attainment target.")
        lines.append("  No corrective actions required.")
    else:
        lines.append(f"  {len(a['atr_rows'])} PO(s) below target:")
        lines.append("")
        for p in a["atr_rows"]:
            lines.append(f"  {p['po']} - {p['name'][:40]}  |  {p['pct']:.1f}%  (Level {p['level']})")
            lines.append(f"    Action Taken: {p.get('atr', '') or 'Not specified'}")
            lines.append("")
    lines.append("")

    return "\n".join(lines)


def _rule_readiness(a):
    score = 0
    if a["pomap_rows"]:          score += 20
    if a["co_results"]:          score += 20
    if a["po_attainment"]:       score += 20
    if a["sdgco_contrib"]:       score += 10
    if a["sdgpo_results"]:       score += 10
    if a["mean_att_pct"] >= 60:  score += 10
    if len(a["sdgs_covered"]) >= 2: score += 10
    return score


# ── TXT output ────────────────────────────────────────────────────────────────

def build_txt(pomap_data, coatt_data, poatt_data, sdgco_data, sdgpo_data,
              analytics, ai, code, title, semester, output_path):
    txt = _build_txt(pomap_data, coatt_data, poatt_data, sdgco_data, sdgpo_data,
                     analytics, ai, code, title, semester)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(txt)


# ── DOCX output ───────────────────────────────────────────────────────────────

def build_docx(pomap_data, coatt_data, poatt_data, sdgco_data, sdgpo_data,
               analytics, ai, code, title, semester, output_path):
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    a   = analytics
    now = datetime.datetime.now().strftime("%d %b %Y")
    sem = f"Semester {semester}  |  " if semester else ""

    doc = Document()

    # narrow margins
    for sec in doc.sections:
        sec.top_margin    = Inches(0.75)
        sec.bottom_margin = Inches(0.75)
        sec.left_margin   = Inches(0.9)
        sec.right_margin  = Inches(0.9)

    GREEN  = RGBColor(5, 150, 105)   # #059669
    DGREEN = RGBColor(1, 91, 63)
    BLACK  = RGBColor(17, 24, 39)
    GREY   = RGBColor(107, 114, 128)

    def _s(v): return str(v) if v is not None else ""

    def add_title(text):
        p = doc.add_heading(text, level=0)
        p.runs[0].font.color.rgb = DGREEN
        p.runs[0].font.size = Pt(16)
        p.paragraph_format.space_after = Pt(4)

    def add_h1(text):
        p = doc.add_heading(text, level=1)
        for run in p.runs:
            run.font.color.rgb = GREEN
            run.font.size = Pt(12)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after  = Pt(4)

    def add_para(text, size=10, bold=False, color=None, indent=False):
        p = doc.add_paragraph()
        if indent:
            p.paragraph_format.left_indent = Inches(0.25)
        run = p.add_run(text)
        run.font.size  = Pt(size)
        run.font.bold  = bold
        run.font.color.rgb = color or BLACK
        p.paragraph_format.space_after = Pt(2)
        return p

    def add_kv(key, val):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.space_after = Pt(2)
        r1 = p.add_run(key + ": ")
        r1.font.bold = True
        r1.font.size = Pt(10)
        r2 = p.add_run(_s(val))
        r2.font.size = Pt(10)

    def _insert_chart(buf, width=5.2):
        if buf is None:
            return
        import tempfile as _tf, os as _os2
        _fname = None
        try:
            with _tf.NamedTemporaryFile(delete=False, suffix='.png') as _f:
                _f.write(buf.read())
                _fname = _f.name
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(_fname, width=Inches(width))
            doc.add_paragraph().paragraph_format.space_after = Pt(4)
        except Exception:
            pass
        finally:
            if _fname:
                try:
                    _os2.unlink(_fname)
                except Exception:
                    pass

    # Title
    add_title("Module 4 Comprehensive Assessment Report")
    sub = doc.add_paragraph(f"{title} ({code})  |  {sem}Generated: {now}")
    sub.runs[0].font.size  = Pt(9)
    sub.runs[0].font.color.rgb = GREY
    sub.paragraph_format.space_after = Pt(8)

    # 1. Course Overview
    add_h1("1. Course Overview")
    add_kv("Course Code",          code)
    add_kv("Course Title",         title)
    add_kv("Course Outcomes",      a["n_cos"])
    add_kv("Programme Outcomes",   a["n_pos"])
    add_kv("Mean CO Attainment",   f"{a['mean_att_pct']}%")
    add_kv("SDG Focus (CO-level)", a["target_sdg"] or "N/A")
    add_kv("SDGs Covered (PO)",    len(a["sdgs_covered"]))
    doc.add_paragraph()

    # 2. CO-PO Mapping Table
    add_h1("2. CO-PO-PSO Mapping Table")
    add_para("3 = Strong  |  2 = Moderate  |  1 = Low  |  0 = None",
             size=9, color=GREY, indent=True)
    if a["pomap_rows"]:
        pk   = a["po_keys"]
        tbl  = doc.add_table(rows=1 + len(a["pomap_rows"]), cols=1 + len(pk))
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        hdr[0].text = "CO"
        for i, k in enumerate(pk):
            hdr[i + 1].text = k
        for ridx, row in enumerate(a["pomap_rows"]):
            cells = tbl.rows[ridx + 1].cells
            cells[0].text = _s(row.get("co", ""))
            for i, k in enumerate(pk):
                cells[i + 1].text = _s(row.get("scores", {}).get(k, 0))
        # header row bold
        for cell in tbl.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
        doc.add_paragraph()
    if _rc:
        _insert_chart(_rc.copo_heatmap(a["pomap_rows"], a["po_keys"]))

    # 3. CO Strength Summary
    add_h1("3. CO Strength Summary (Average PO Score)")
    if a["co_strength"]:
        tbl = doc.add_table(rows=1 + len(a["co_strength"]), cols=3)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        for i, h in enumerate(["CO", "Avg PO Score", "Interpretation"]):
            hdr[i].text = h
        for i, (co, avg) in enumerate(a["co_strength"].items()):
            interp = "Strong" if avg >= 2 else "Moderate" if avg >= 1 else "Low"
            cells = tbl.rows[i + 1].cells
            cells[0].text = co
            cells[1].text = f"{avg:.2f}"
            cells[2].text = interp
        for cell in tbl.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
        doc.add_paragraph()

    # 4. CO Attainment Analysis
    add_h1("4. CO Attainment Analysis")
    t = a["thresholds"]
    add_para(f"Thresholds: Level 3 >= {t['t1']}%  |  Level 2 >= {t['t2']}%  |  Level 1 >= {t['t3']}%",
             size=9, color=GREY, indent=True)
    if a["co_results"]:
        tbl = doc.add_table(rows=1 + len(a["co_results"]), cols=3)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        for i, h in enumerate(["CO", "Attainment %", "Level"]):
            hdr[i].text = h
        for i, r in enumerate(a["co_results"]):
            cells = tbl.rows[i + 1].cells
            cells[0].text = _s(r.get("co", ""))
            cells[1].text = f"{r['pct']:.2f}%"
            cells[2].text = _s(r.get("level", 0))
        for cell in tbl.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
    add_kv("Mean CO Attainment", f"{a['mean_att_pct']}%")
    doc.add_paragraph()
    if _rc:
        _insert_chart(_rc.co_attainment_chart(a["co_results"], a["thresholds"]))

    # 5. PO Attainment Summary
    add_h1("5. PO Attainment Summary")
    if a["po_results"]:
        tbl = doc.add_table(rows=2, cols=len(a["po_results"]))
        tbl.style = "Table Grid"
        for i, r in enumerate(a["po_results"]):
            tbl.rows[0].cells[i].text = _s(r.get("po", ""))
            tbl.rows[1].cells[i].text = f"{r['attainment']:.2f}"
        for cell in tbl.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
    doc.add_paragraph()

    # 5b. PO Attainment Analysis
    add_h1("5b. PO Attainment Analysis (NBA Method)")
    if a["po_attainment"]:
        pa_sum = a["po_att_summary"]
        add_kv("Mean PO Attainment",   f"{pa_sum.get('mean_pct', 0):.1f}%")
        add_kv("POs Meeting Target",   f"{pa_sum.get('pos_meeting_target', 0)} / {len(a['po_attainment'])}")
        tbl = doc.add_table(rows=1 + len(a["po_attainment"]), cols=5)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        for i, h in enumerate(["PO", "Name", "Attainment %", "Level", "Target"]):
            hdr[i].text = h
        for ridx, p in enumerate(a["po_attainment"]):
            cells = tbl.rows[ridx + 1].cells
            cells[0].text = _s(p.get("po", ""))
            cells[1].text = _s(p.get("name", ""))
            cells[2].text = f"{p['pct']:.1f}%"
            cells[3].text = _s(p.get("level", 0))
            cells[4].text = "Met" if p.get("target_met") else "Below"
        for cell in tbl.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
    else:
        add_para("Run PO Attainment tool to see this section.", indent=True)
    doc.add_paragraph()
    if _rc:
        _insert_chart(_rc.po_attainment_chart(a["po_attainment"]))

    # 6. Attainment Level Distribution
    add_h1("6. Attainment Level Distribution")
    ld  = a["level_dist"]
    tbl = doc.add_table(rows=2, cols=4)
    tbl.style = "Table Grid"
    for i, lv in enumerate([3, 2, 1, 0]):
        tbl.rows[0].cells[i].text = f"Level {lv}"
        tbl.rows[1].cells[i].text = f"{ld.get(lv, 0)} CO(s)"
    for cell in tbl.rows[0].cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
    doc.add_paragraph()
    if _rc:
        _insert_chart(_rc.attainment_level_chart(a["level_dist"]))

    # 7. CO to SDG Contribution
    add_h1("7. CO to SDG Contribution Analysis")
    if a["sdgco_contrib"]:
        add_kv("Target SDG", a["target_sdg"])
        tbl = doc.add_table(rows=1 + len(a["sdgco_contrib"]), cols=4)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        for i, h in enumerate(["CO", "Statement", "Score", "Share %"]):
            hdr[i].text = h
        for i, c in enumerate(a["sdgco_contrib"]):
            cells = tbl.rows[i + 1].cells
            cells[0].text = _s(c.get("co", ""))
            cells[1].text = _s(c.get("statement", ""))
            cells[2].text = _s(c.get("score", 0))
            cells[3].text = f"{c.get('pct', 0):.1f}%"
        for cell in tbl.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
        add_kv("Total Score", a["sdgco_total"])
    else:
        add_para("No CO-SDG data available.", indent=True)
    doc.add_paragraph()

    # 8. PO to SDG Contribution
    add_h1("8. PO to SDG Contribution Analysis")
    if a["sdgpo_results"]:
        tbl = doc.add_table(rows=1 + len(a["sdgpo_results"]), cols=3)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        for i, h in enumerate(["SDG", "Contribution %", "Interpretation"]):
            hdr[i].text = h
        for i, r in enumerate(a["sdgpo_results"]):
            cells = tbl.rows[i + 1].cells
            cells[0].text = _s(r.get("sdg", ""))
            cells[1].text = f"{r.get('contribution', 0):.2f}%"
            cells[2].text = _s(r.get("interpretation", ""))
        for cell in tbl.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
    else:
        add_para("No PO-SDG data available.", indent=True)
    doc.add_paragraph()

    # 9. Composite SDG Index
    add_h1("9. Composite SDG Index")
    interp = ("Excellent" if a["sdgpo_composite"] >= 85 else
              "Strong"    if a["sdgpo_composite"] >= 70 else
              "Moderate"  if a["sdgpo_composite"] >= 50 else "Weak")
    add_kv("Composite SDG Index", f"{a['sdgpo_composite']:.2f}%")
    add_kv("Interpretation",      interp)
    doc.add_paragraph()

    # 10. NBA/NAAC Compliance Checklist
    add_h1("10. NBA/NAAC Assessment Compliance Checklist")
    has_atr = (not a["atr_rows"]) or all(p.get("atr", "").strip() for p in a["atr_rows"])
    checks = [
        ("CO-PO Mapping generated",                    bool(a["pomap_rows"])),
        ("CO Attainment calculated",                   bool(a["co_results"])),
        ("CO-level SDG contribution mapped",           bool(a["sdgco_contrib"])),
        ("PO-level SDG contribution mapped",           bool(a["sdgpo_results"])),
        ("Mean CO attainment >= 60%",                  a["mean_att_pct"] >= 60),
        ("Multiple SDGs covered",                      len(a["sdgs_covered"]) >= 2),
        ("Action Taken Report documented",             has_atr),
    ]
    tbl = doc.add_table(rows=1 + len(checks), cols=2)
    tbl.style = "Table Grid"
    tbl.rows[0].cells[0].text = "Criterion"
    tbl.rows[0].cells[1].text = "Status"
    for i, (label, ok) in enumerate(checks):
        tbl.rows[i + 1].cells[0].text = label
        tbl.rows[i + 1].cells[1].text = "Met" if ok else "Needs Attention"
    for cell in tbl.rows[0].cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
    doc.add_paragraph()

    # 11. Assessment Readiness Dashboard
    add_h1("11. Assessment Readiness Dashboard")
    if ai:
        add_kv("Readiness Score", f"{ai.get('readiness_score', 'N/A')}/100")
        if ai.get("attainment_quality"):
            add_kv("Attainment Quality",  ai["attainment_quality"])
        if ai.get("mapping_strength"):
            add_kv("Mapping Strength",    ai["mapping_strength"])
        if ai.get("sdg_integration"):
            add_kv("SDG Integration",     ai["sdg_integration"])
        if ai.get("nba_compliance"):
            add_kv("NBA/NAAC Compliance", ai["nba_compliance"])
        recs = ai.get("recommendations", [])
        if recs:
            add_para("Recommendations:", bold=True, indent=True)
            for i, r in enumerate(recs, 1):
                add_para(f"{i}. {r}", indent=True)
    else:
        score = _rule_readiness(a)
        add_kv("Readiness Score", f"{score}/100")
    doc.add_paragraph()

    # 12. Action Taken Report
    add_h1("12. Action Taken Report")
    add_para("Corrective actions for Programme Outcomes below attainment target.",
             size=9, color=GREY, indent=True)
    if not a["po_attainment"]:
        add_para("Run PO Attainment tool to generate this section.", indent=True)
    elif not a["atr_rows"]:
        add_para("All Programme Outcomes met attainment target. No corrective actions required.",
                 indent=True, color=GREEN)
    else:
        add_para(f"{len(a['atr_rows'])} PO(s) below target — corrective actions recorded below.",
                 indent=True)
        tbl = doc.add_table(rows=1 + len(a["atr_rows"]), cols=5)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        for i, h in enumerate(["PO", "Name", "Attainment %", "Level", "Action Taken"]):
            hdr[i].text = h
        for ridx, p in enumerate(a["atr_rows"]):
            cells = tbl.rows[ridx + 1].cells
            cells[0].text = _s(p.get("po", ""))
            cells[1].text = _s(p.get("name", ""))
            cells[2].text = f"{p['pct']:.1f}%"
            cells[3].text = _s(p.get("level", 0))
            cells[4].text = _s(p.get("atr", "")) or "Not specified"
        for cell in tbl.rows[0].cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
    doc.add_paragraph()

    doc.save(output_path)


# ── PDF output ────────────────────────────────────────────────────────────────

def build_pdf(pomap_data, coatt_data, poatt_data, sdgco_data, sdgpo_data,
              analytics, ai, code, title, semester, output_path):
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    a   = analytics
    now = datetime.datetime.now().strftime("%d %b %Y")
    sem = f"Semester {semester}  |  " if semester else ""

    def _s(v): return str(v) if v is not None else ""

    def _safe(s):
        return str(s).encode("latin-1", "replace").decode("latin-1")

    def _pdf_chart(buf, w=155):
        if buf is None or _rc is None:
            return
        import tempfile as _tf, os as _os2
        _fname = None
        try:
            with _tf.NamedTemporaryFile(delete=False, suffix='.png') as _f:
                _f.write(buf.read())
                _fname = _f.name
            x = pdf.l_margin + (180 - w) / 2
            pdf.image(_fname, x=x, w=w)
            pdf.ln(3)
        except Exception:
            pdf.set_x(pdf.l_margin)
        finally:
            if _fname:
                try:
                    _os2.unlink(_fname)
                except Exception:
                    pass

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def h1(text):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(5, 150, 105)
        pdf.cell(0, 8, _safe(_s(text)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1)

    def h2(text):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(1, 91, 63)
        pdf.cell(0, 7, _safe(_s(text)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    def kv(key, val):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(55, 6, _safe(_s(key)) + ":", border=0)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.multi_cell(0, 6, _safe(_s(val)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Cover
    h1("Module 4 Comprehensive Assessment Report")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(107, 114, 128)
    pdf.cell(0, 5, _safe(f"{title} ({code})  |  {sem}Generated: {now}"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # 1. Overview
    h2("1. Course Overview")
    kv("Course Outcomes", a["n_cos"])
    kv("Programme Outcomes", a["n_pos"])
    kv("Mean CO Attainment", f"{a['mean_att_pct']}%")
    kv("SDG Focus (CO)", a["target_sdg"] or "N/A")
    kv("SDGs Covered (PO)", len(a["sdgs_covered"]))
    pdf.ln(3)

    # 2. CO-PO Mapping
    h2("2. CO-PO Mapping Table")
    if a["pomap_rows"]:
        pk      = a["po_keys"]
        avail_w = pdf.w - pdf.l_margin - pdf.r_margin
        co_col  = 28
        cw      = max(8, int((avail_w - co_col) / max(len(pk), 1)))
        fs      = 7 if cw < 11 else 8
        pdf.set_font("Helvetica", "B", fs)
        pdf.set_fill_color(209, 250, 229)
        pdf.cell(co_col, 6, "CO", border=1, fill=True, align="C")
        for k in pk:
            pdf.cell(cw, 6, k, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", fs)
        for row in a["pomap_rows"]:
            pdf.cell(co_col, 5, _s(row.get("co", "")), border=1)
            for k in pk:
                pdf.cell(cw, 5, _s(row.get("scores", {}).get(k, 0)), border=1, align="C")
            pdf.ln()
    pdf.ln(3)
    _pdf_chart(_rc.copo_heatmap(a["pomap_rows"], a["po_keys"]) if _rc else None)

    # 4. CO Attainment
    h2("4. CO Attainment Analysis")
    t = a["thresholds"]
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, f"Level 3 >= {t['t1']}%  |  Level 2 >= {t['t2']}%  |  Level 1 >= {t['t3']}%",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if a["co_results"]:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(209, 250, 229)
        for lbl, w in [("CO", 40), ("Attainment %", 55), ("Level", 40)]:
            pdf.cell(w, 7, lbl, border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for r in a["co_results"]:
            pdf.cell(40, 6, _s(r.get("co", "")), border=1)
            pdf.cell(55, 6, f"{r['pct']:.2f}%", border=1, align="C")
            pdf.cell(40, 6, _s(r.get("level", 0)), border=1, align="C")
            pdf.ln()
    kv("Mean CO Attainment", f"{a['mean_att_pct']}%")
    pdf.ln(3)
    _pdf_chart(_rc.co_attainment_chart(a["co_results"], a["thresholds"]) if _rc else None)

    # 5. PO Attainment
    h2("5. PO Attainment Summary")
    if a["po_results"]:
        avail_w = pdf.w - pdf.l_margin - pdf.r_margin
        col_w = max(10, int(avail_w / max(len(a["po_results"]), 1)))
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(209, 250, 229)
        for r in a["po_results"]:
            pdf.cell(col_w, 6, _s(r["po"]), border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for r in a["po_results"]:
            pdf.cell(col_w, 5, f"{r['attainment']:.2f}", border=1, align="C")
        pdf.ln()
    pdf.ln(3)

    # 5b. PO Attainment
    h2("5b. PO Attainment Analysis (NBA Method)")
    if a["po_attainment"]:
        pa_sum = a["po_att_summary"]
        kv("Mean PO Attainment",  f"{pa_sum.get('mean_pct', 0):.1f}%")
        kv("POs Meeting Target",  f"{pa_sum.get('pos_meeting_target', 0)} / {len(a['po_attainment'])}")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(209, 250, 229)
        for lbl, w in [("PO", 15), ("Name", 70), ("Att%", 20), ("Level", 15), ("Target", 25)]:
            pdf.cell(w, 7, lbl, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 8.5)
        for p in a["po_attainment"]:
            pdf.cell(15, 5.5, _s(p.get("po", "")), border=1)
            pdf.cell(70, 5.5, _s(p.get("name", ""))[:38], border=1)
            pdf.cell(20, 5.5, f"{p['pct']:.1f}%", border=1, align="C")
            pdf.cell(15, 5.5, _s(p.get("level", 0)), border=1, align="C")
            pdf.cell(25, 5.5, "Met" if p.get("target_met") else "Below", border=1, align="C")
            pdf.ln()
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, "Run PO Attainment tool to populate this section.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)
    _pdf_chart(_rc.po_attainment_chart(a["po_attainment"]) if _rc else None)

    # 7. CO-SDG
    h2("7. CO to SDG Contribution")
    if a["sdgco_contrib"]:
        kv("Target SDG", a["target_sdg"])
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(209, 250, 229)
        for lbl, w in [("CO", 25), ("Score", 25), ("Share %", 30)]:
            pdf.cell(w, 7, lbl, border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for c in a["sdgco_contrib"]:
            pdf.cell(25, 6, _s(c.get("co", "")), border=1)
            pdf.cell(25, 6, _s(c.get("score", 0)), border=1, align="C")
            pdf.cell(30, 6, f"{c.get('pct', 0):.1f}%", border=1, align="C")
            pdf.ln()
        kv("Total Score", a["sdgco_total"])
    pdf.ln(3)

    # 8. PO-SDG
    h2("8. PO to SDG Contribution")
    if a["sdgpo_results"]:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(209, 250, 229)
        for lbl, w in [("SDG", 100), ("Contribution %", 40), ("Interpretation", 40)]:
            pdf.cell(w, 7, lbl, border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for r in a["sdgpo_results"]:
            pdf.cell(100, 6, _safe(_s(r.get("sdg", "")))[:55], border=1)
            pdf.cell(40,  6, f"{r.get('contribution', 0):.2f}%", border=1, align="C")
            pdf.cell(40,  6, _safe(_s(r.get("interpretation", ""))), border=1, align="C")
            pdf.ln()
    pdf.ln(3)

    # 9. Composite SDG
    h2("9. Composite SDG Index")
    interp = ("Excellent" if a["sdgpo_composite"] >= 85 else
              "Strong"    if a["sdgpo_composite"] >= 70 else
              "Moderate"  if a["sdgpo_composite"] >= 50 else "Weak")
    kv("Composite SDG Index", f"{a['sdgpo_composite']:.2f}%  ({interp})")
    pdf.ln(3)

    # 10. Checklist
    h2("10. NBA/NAAC Assessment Compliance Checklist")
    has_atr = (not a["atr_rows"]) or all(p.get("atr", "").strip() for p in a["atr_rows"])
    checks = [
        ("CO-PO Mapping generated",                    bool(a["pomap_rows"])),
        ("CO Attainment calculated",                   bool(a["co_results"])),
        ("CO-level SDG contribution mapped",           bool(a["sdgco_contrib"])),
        ("PO-level SDG contribution mapped",           bool(a["sdgpo_results"])),
        ("Mean CO attainment >= 60%",                  a["mean_att_pct"] >= 60),
        ("Multiple SDGs covered",                      len(a["sdgs_covered"]) >= 2),
        ("Action Taken Report documented",             has_atr),
    ]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(209, 250, 229)
    pdf.cell(130, 7, "Criterion", border=1, fill=True)
    pdf.cell(50,  7, "Status",    border=1, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for label, ok in checks:
        pdf.cell(130, 6, label, border=1)
        pdf.cell(50,  6, "Met" if ok else "Needs Attention", border=1, align="C")
        pdf.ln()
    pdf.ln(3)

    # 11. Dashboard
    h2("11. Assessment Readiness Dashboard")
    if ai:
        kv("Readiness Score", f"{ai.get('readiness_score', 'N/A')}/100")
        for fld, lbl in [
            ("attainment_quality", "Attainment Quality"),
            ("mapping_strength",   "Mapping Strength"),
            ("sdg_integration",    "SDG Integration"),
            ("nba_compliance",     "NBA/NAAC Compliance"),
        ]:
            if ai.get(fld):
                kv(lbl, ai[fld])
        recs = ai.get("recommendations", [])
        if recs:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, "Recommendations:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 9)
            for i, r in enumerate(recs, 1):
                pdf.multi_cell(0, 5.5, _safe(f"{i}. {r}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        score = _rule_readiness(a)
        kv("Readiness Score", f"{score}/100")
    pdf.ln(3)

    # 12. Action Taken Report
    h2("12. Action Taken Report")
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Corrective actions for Programme Outcomes below attainment target.",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    if not a["po_attainment"]:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, "Run PO Attainment tool to generate this section.",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    elif not a["atr_rows"]:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(5, 150, 105)
        pdf.cell(0, 5, "All Programme Outcomes met attainment target. No corrective actions required.",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"{len(a['atr_rows'])} PO(s) below target:",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(209, 250, 229)
        for lbl, w in [("PO", 15), ("Name", 55), ("Att%", 18), ("Level", 15), ("Action Taken", 77)]:
            pdf.cell(w, 7, lbl, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 8.5)
        for p in a["atr_rows"]:
            atr_text = (_s(p.get("atr", "")) or "Not specified")[:42]
            pdf.cell(15, 5.5, _s(p.get("po", "")),           border=1)
            pdf.cell(55, 5.5, _s(p.get("name", ""))[:30],    border=1)
            pdf.cell(18, 5.5, f"{p['pct']:.1f}%",            border=1, align="C")
            pdf.cell(15, 5.5, _s(p.get("level", 0)),         border=1, align="C")
            pdf.cell(77, 5.5, atr_text,                       border=1)
            pdf.ln()
    pdf.ln(3)

    pdf.output(output_path)
