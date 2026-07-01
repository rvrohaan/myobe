"""Chart generation utilities for MyOBE module reports.

Each function returns a BytesIO PNG buffer for embedding in DOCX/PDF,
or None if data is insufficient to draw a meaningful chart.
"""
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

_C_INDIGO = '#312E81'
_C_TEAL   = '#064E5B'
_C_GREEN  = '#059669'
_C_AMBER  = '#B45309'
_C_RED    = '#DC2626'
_PALETTE  = [_C_INDIGO, _C_GREEN, '#0891B2', _C_AMBER, _C_RED, '#7C3AED', '#D97706', '#0E7490']


def _buf(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=130, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


# ── M4: Assessment & Outcomes ─────────────────────────────────────────────────

def co_attainment_chart(co_results, thresholds):
    """Horizontal bar chart of CO attainment % with Level 2/3 threshold markers."""
    if not co_results:
        return None
    labels = [r.get('co', '') for r in co_results]
    values = [float(r.get('pct', 0)) for r in co_results]
    t1 = float(thresholds.get('t1', 70))
    t2 = float(thresholds.get('t2', 60))
    colors = [_C_GREEN if v >= t1 else _C_AMBER if v >= t2 else _C_RED for v in values]

    fig, ax = plt.subplots(figsize=(6.5, max(2.5, len(labels) * 0.48 + 0.6)))
    bars = ax.barh(labels, values, color=colors, height=0.55,
                   edgecolor='white', linewidth=0.5)
    ax.axvline(t1, color=_C_GREEN, linestyle='--', linewidth=1.2,
               label=f'L3 threshold ({int(t1)}%)')
    ax.axvline(t2, color=_C_AMBER, linestyle=':', linewidth=1.2,
               label=f'L2 threshold ({int(t2)}%)')
    ax.set_xlim(0, 112)
    ax.set_xlabel('Attainment %', fontsize=9)
    ax.set_title('CO Attainment Analysis', fontsize=11, fontweight='bold', color=_C_INDIGO)
    ax.legend(fontsize=8, loc='lower right')
    for bar, val in zip(bars, values):
        ax.text(val + 1.2, bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}%', va='center', ha='left', fontsize=8)
    ax.tick_params(axis='y', labelsize=9)
    ax.tick_params(axis='x', labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)


def po_attainment_chart(po_attainment):
    """Horizontal bar chart of PO attainment % coloured by target-met status."""
    if not po_attainment:
        return None
    labels = [p.get('po', '') for p in po_attainment]
    values = [float(p.get('pct', 0)) for p in po_attainment]
    met    = [p.get('target_met', False) for p in po_attainment]
    colors = [_C_GREEN if m else _C_RED for m in met]

    fig, ax = plt.subplots(figsize=(6.5, max(2.5, len(labels) * 0.44 + 0.6)))
    bars = ax.barh(labels, values, color=colors, height=0.5,
                   edgecolor='white', linewidth=0.5)
    ax.axvline(60, color=_C_AMBER, linestyle='--', linewidth=1.2, label='Target (60%)')
    ax.set_xlim(0, 112)
    ax.set_xlabel('Attainment %', fontsize=9)
    ax.set_title('PO Attainment', fontsize=11, fontweight='bold', color=_C_INDIGO)
    ax.legend(fontsize=8)
    for bar, val in zip(bars, values):
        ax.text(val + 1.2, bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}%', va='center', ha='left', fontsize=8)
    ax.tick_params(axis='y', labelsize=9)
    ax.tick_params(axis='x', labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)


def attainment_level_chart(level_dist):
    """Bar chart showing the count of COs at each attainment level (0-3)."""
    levels = [3, 2, 1, 0]
    values = [level_dist.get(l, 0) for l in levels]
    if sum(values) == 0:
        return None
    labels = ['Level 3', 'Level 2', 'Level 1', 'Level 0']
    colors = [_C_GREEN, '#0891B2', _C_AMBER, _C_RED]

    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    bars = ax.bar(labels, values, color=colors, width=0.5,
                  edgecolor='white', linewidth=0.5)
    ax.set_ylabel('Number of COs', fontsize=9)
    ax.set_title('Attainment Level Distribution', fontsize=11, fontweight='bold', color=_C_INDIGO)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.05,
                    str(val), ha='center', va='bottom', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)


def co_attainment_compare_chart(co_compare):
    """Grouped horizontal bars per CO: marks-based vs AI attainment level (0-3)."""
    if not co_compare:
        return None
    labels  = [c.get('co', '') for c in co_compare]
    marks_v = [float(c.get('marks_level') or 0) for c in co_compare]
    ai_v    = [float(c.get('ai_level')) if c.get('ai_level') is not None else 0.0
               for c in co_compare]

    y = np.arange(len(labels))
    h = 0.38
    fig, ax = plt.subplots(figsize=(6.5, max(2.5, len(labels) * 0.6 + 0.8)))
    b1 = ax.barh(y + h / 2, marks_v, height=h, color=_C_GREEN,
                 edgecolor='white', linewidth=0.5, label='Marks-based')
    b2 = ax.barh(y - h / 2, ai_v, height=h, color=_C_INDIGO,
                 edgecolor='white', linewidth=0.5, label='AI-estimated')
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 3.4)
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xlabel('Attainment Level (0-3)', fontsize=9)
    ax.set_title('CO Attainment: Marks-Based vs AI', fontsize=11,
                 fontweight='bold', color=_C_INDIGO)
    ax.legend(fontsize=8, loc='lower right')
    for bars in (b1, b2):
        for bar in bars:
            w = bar.get_width()
            ax.text(w + 0.05, bar.get_y() + bar.get_height() / 2,
                    f'{w:.2f}', va='center', ha='left', fontsize=7.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)


def copo_heatmap(pomap_rows, po_keys):
    """Color-coded heatmap of the CO-PO mapping matrix (scores 0-3)."""
    if not pomap_rows or not po_keys:
        return None
    co_labels = [r.get('co', f'CO{i+1}') for i, r in enumerate(pomap_rows)]
    matrix = np.array([
        [float(r.get('scores', {}).get(pk, 0) or 0) for pk in po_keys]
        for r in pomap_rows
    ])
    cmap = LinearSegmentedColormap.from_list(
        'obe_green', ['#F9FAFB', '#BBF7D0', '#34D399', '#065F46'], N=256
    )
    fig_w = max(5.0, len(po_keys) * 0.58 + 1.2)
    fig_h = max(2.5, len(co_labels) * 0.52 + 0.8)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=3, aspect='auto')
    ax.set_xticks(range(len(po_keys)))
    ax.set_xticklabels(po_keys, fontsize=8, rotation=45, ha='right')
    ax.set_yticks(range(len(co_labels)))
    ax.set_yticklabels(co_labels, fontsize=9)
    for i in range(len(co_labels)):
        for j in range(len(po_keys)):
            val = int(matrix[i, j])
            ax.text(j, i, str(val), ha='center', va='center',
                    fontsize=9, color='white' if val >= 2 else '#374151')
    cbar = plt.colorbar(im, ax=ax, ticks=[0, 1, 2, 3])
    cbar.set_ticklabels(['0 None', '1 Low', '2 Mod', '3 Strong'], fontsize=7)
    ax.set_title('CO-PO Mapping Heatmap', fontsize=11, fontweight='bold', color=_C_INDIGO)
    fig.tight_layout()
    return _buf(fig)


# ── M3: Course Delivery ───────────────────────────────────────────────────────

def bloom_distribution_chart(bloom_dist):
    """Horizontal bar chart of Bloom's taxonomy level counts across COs."""
    if not bloom_dist:
        return None
    items  = sorted(bloom_dist.items(), key=lambda x: x[1], reverse=True)
    labels = [i[0] for i in items]
    values = [i[1] for i in items]

    fig, ax = plt.subplots(figsize=(5.5, max(2.0, len(labels) * 0.48 + 0.5)))
    bars = ax.barh(labels, values, color=_C_INDIGO, height=0.5,
                   edgecolor='white', linewidth=0.5)
    ax.set_xlabel('Number of COs', fontsize=9)
    ax.set_title("Bloom's Taxonomy Distribution", fontsize=11, fontweight='bold', color=_C_INDIGO)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    for bar, val in zip(bars, values):
        ax.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                str(val), va='center', ha='left', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)


def co_session_chart(cos, co_session_tally):
    """Bar chart of session count per CO."""
    if not cos:
        return None
    labels = [f"CO{c['num']}" for c in cos]
    values = [co_session_tally.get(f"CO{c['num']}", 0) for c in cos]
    if sum(values) == 0:
        return None
    colors = [_C_GREEN if v > 0 else _C_RED for v in values]

    fig, ax = plt.subplots(figsize=(max(4.0, len(labels) * 0.72 + 1.0), 3.5))
    bars = ax.bar(labels, values, color=colors, width=0.5,
                  edgecolor='white', linewidth=0.5)
    ax.set_ylabel('Sessions', fontsize=9)
    ax.set_title('Sessions Allocated per CO', fontsize=11, fontweight='bold', color=_C_INDIGO)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.05,
                    str(val), ha='center', va='bottom', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)


def teaching_method_chart(method_dist):
    """Pie chart of teaching method distribution across sessions."""
    if not method_dist or sum(method_dist.values()) == 0:
        return None
    labels = list(method_dist.keys())
    values = list(method_dist.values())

    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    wedges, _, autotexts = ax.pie(
        values, autopct='%1.0f%%',
        colors=_PALETTE[:len(labels)],
        startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
        pctdistance=0.78,
    )
    for at in autotexts:
        at.set_fontsize(8)
    ax.legend(wedges, labels, loc='lower right', fontsize=8,
              bbox_to_anchor=(1.3, -0.05))
    ax.set_title('Teaching Method Distribution', fontsize=11, fontweight='bold', color=_C_INDIGO)
    fig.tight_layout()
    return _buf(fig)


# ── M1: Question Bank & Assessment ───────────────────────────────────────────

def difficulty_pie_chart(diff_dist):
    """Pie chart of question difficulty distribution (Easy/Medium/Hard)."""
    if not diff_dist or sum(diff_dist.values()) == 0:
        return None
    labels = list(diff_dist.keys())
    values = list(diff_dist.values())
    colors = [_C_GREEN, _C_AMBER, _C_RED, '#0891B2'][:len(labels)]

    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    wedges, _, autotexts = ax.pie(
        values, autopct='%1.1f%%',
        colors=colors, startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
        pctdistance=0.78,
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.legend(wedges, labels, loc='lower right', fontsize=9,
              bbox_to_anchor=(1.35, -0.05))
    ax.set_title('Question Difficulty Distribution', fontsize=11, fontweight='bold', color=_C_INDIGO)
    fig.tight_layout()
    return _buf(fig)


def qqi_chart(qqi_scores, overall_qqi):
    """Horizontal bar chart of QQI scores per CO with overall average line."""
    if not qqi_scores:
        return None
    labels = list(qqi_scores.keys())
    values = [float(v) for v in qqi_scores.values()]
    colors = [_C_GREEN if v >= 70 else _C_AMBER if v >= 50 else _C_RED for v in values]

    fig, ax = plt.subplots(figsize=(5.5, max(2.5, len(labels) * 0.48 + 0.6)))
    bars = ax.barh(labels, values, color=colors, height=0.5,
                   edgecolor='white', linewidth=0.5)
    ax.axvline(overall_qqi, color=_C_INDIGO, linestyle='--', linewidth=1.2,
               label=f'Overall QQI ({overall_qqi})')
    ax.set_xlim(0, 112)
    ax.set_xlabel('QQI Score (0-100)', fontsize=9)
    ax.set_title('Question Quality Index per CO', fontsize=11, fontweight='bold', color=_C_INDIGO)
    ax.legend(fontsize=8)
    for bar, val in zip(bars, values):
        ax.text(val + 1.2, bar.get_y() + bar.get_height() / 2,
                str(int(val)), va='center', ha='left', fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)


def co_marks_chart(cos, co_marks, total_marks):
    """Bar chart of total marks in QB per CO."""
    if not cos or not co_marks or not total_marks:
        return None
    labels = [f"CO{c['num']}" for c in cos]
    values = [co_marks.get(str(c['num']), 0) for c in cos]
    if sum(values) == 0:
        return None

    fig, ax = plt.subplots(figsize=(max(4.0, len(labels) * 0.72 + 1.0), 3.5))
    bars = ax.bar(labels, values, color=_C_TEAL, width=0.5,
                  edgecolor='white', linewidth=0.5)
    ax.set_ylabel('Marks in QB', fontsize=9)
    ax.set_title('CO-wise Marks Distribution', fontsize=11, fontweight='bold', color=_C_INDIGO)
    for bar, val in zip(bars, values):
        if val > 0:
            pct = round(val / total_marks * 100)
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.2,
                    f'{val}\n({pct}%)', ha='center', va='bottom', fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)


def accreditation_metrics_chart(key_metrics):
    """Horizontal bar chart of accreditation readiness key metrics."""
    if not key_metrics:
        return None
    labels = [m.get('metric', '') for m in key_metrics]
    values = [float(m.get('score', 0)) for m in key_metrics]
    colors = [_C_GREEN if v >= 75 else _C_AMBER if v >= 50 else _C_RED for v in values]

    fig, ax = plt.subplots(figsize=(6.0, max(2.5, len(labels) * 0.5 + 0.6)))
    bars = ax.barh(labels, values, color=colors, height=0.5,
                   edgecolor='white', linewidth=0.5)
    ax.axvline(75, color=_C_GREEN, linestyle='--', linewidth=1.0, alpha=0.7, label='Good (75)')
    ax.axvline(50, color=_C_AMBER, linestyle=':', linewidth=1.0, alpha=0.7, label='Needs Work (50)')
    ax.set_xlim(0, 112)
    ax.set_xlabel('Score (0-100)', fontsize=9)
    ax.set_title('Accreditation Readiness Metrics', fontsize=11, fontweight='bold', color=_C_INDIGO)
    ax.legend(fontsize=8)
    for bar, val in zip(bars, values):
        ax.text(val + 1.2, bar.get_y() + bar.get_height() / 2,
                str(int(val)), va='center', ha='left', fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return _buf(fig)
