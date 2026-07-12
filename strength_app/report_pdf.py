"""
Session-report PDF export (2026-07 burn P1).

A PDF RENDER of the immutable SessionReport.report_json snapshot — zero new
clinical wording. Every string comes verbatim from what report_builder
already produced (both-sides-identical rule: the patient and therapist
endpoints stream byte-identical documents built from the same snapshot).
Pattern follows stretch_pdf.py, the in-repo reference for authenticated
reportlab serving.
"""

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ACCENT = colors.HexColor('#0c6c3f')          # single accent (brand green)
MUTED = colors.HexColor('#475569')
ROW_ALT = colors.HexColor('#f3f4f6')


def _fmt(value, dash='—'):
    return dash if value in (None, '', []) else str(value)


def report_pdf_sections(report):
    """The exact text content the PDF renders, as (section, lines) pairs —
    every line is either verbatim from report_json or a labelled join of
    its fields. Exposed separately so tests can assert the real content
    without parsing compressed PDF streams."""
    header = report.get('header') or {}
    first_name = (header.get('patient_name') or 'Patient').split()[0]

    sections = []
    sections.append(('header', [
        f"{first_name} — {_fmt(header.get('date'))}",
        f"Week {_fmt(header.get('week_number'))} · Session "
        f"{_fmt(header.get('session_number'))} · {_fmt(header.get('status'))}",
        f"Duration {_fmt(header.get('duration_mmss'))} · "
        f"{_fmt(header.get('exercises_done'))}/{_fmt(header.get('exercises_total'))} "
        f"exercises · completion {_fmt(header.get('completion_pct'))}%"
        + (f" · form avg {header.get('form_avg')}%"
           if header.get('form_avg') is not None else ''),
    ]))

    safety = [s for s in (report.get('safety') or []) if s]
    if safety:
        sections.append(('safety', [str(s) for s in safety]))

    if report.get('narrative'):
        sections.append(('narrative', [str(report['narrative'])]))

    for ex in report.get('exercises') or []:
        lines = [f"{_fmt(ex.get('name'))} — {_fmt(ex.get('mode'))}"]
        prescribed = ex.get('prescribed') or {}
        achieved = ex.get('achieved') or {}
        lines.append(
            f"Prescribed {_fmt(prescribed.get('sets'))}×{_fmt(prescribed.get('reps'))}"
            + (f" · tempo {prescribed.get('tempo')}" if prescribed.get('tempo') else '')
            + f" · achieved {_fmt(achieved.get('sets'))} sets "
            f"({_fmt(achieved.get('reps_per_set'))} reps)")
        for s in ex.get('sets') or []:
            lines.append(
                f"Set {_fmt(s.get('set_number'))}: {_fmt(s.get('reps'))} reps"
                + (f", hold {s.get('hold_seconds')}s" if s.get('hold_seconds') else '')
                + (' — self-reported' if s.get('self_reported')
                   else (f" — form {s.get('form_avg')}%"
                         if s.get('form_avg') is not None else ''))
            )
        for c in ex.get('cues') or []:
            lines.append(
                f"Cue: “{_fmt(c.get('text'))}” ×{_fmt(c.get('fired'))}"
                + (f" — {c.get('note')}" if c.get('note') else ''))
        for p in ex.get('pain') or []:
            lines.append(f"Pain: {_fmt(p.get('text'))} — {_fmt(p.get('outcome'))}")
        if ex.get('feedback'):
            lines.append(f"Patient rated it: {ex['feedback']}")
        if ex.get('skipped'):
            lines.append(f"Skipped: {ex['skipped']}")
        sections.append(('exercise', lines))

    patterns = [p.get('evidence') for p in (report.get('patterns') or [])
                if p.get('evidence')]
    review = [r for r in (report.get('review_points') or []) if r]
    summary = patterns + [r for r in review if r not in patterns]
    trends = [t.get('text') or str(t) for t in (report.get('trends') or [])]
    if summary or trends:
        sections.append(('summary', summary + trends))

    if report.get('footer'):
        sections.append(('footer', [str(report['footer'])]))
    return sections


_SECTION_TITLES = {
    'safety': 'Safety',
    'narrative': 'Summary narrative',
    'summary': 'Patterns & review points',
}


def generate_report_pdf(report):
    """report: the SessionReport.report_json dict. Returns BytesIO."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title='VYAYAM Session Report',
        # deterministic output (no random /ID, fixed timestamps) — the
        # both-sides-identical rule is asserted byte-for-byte in tests
        invariant=1,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle('T', fontSize=22, fontName='Helvetica-Bold',
                           textColor=ACCENT, alignment=TA_CENTER, spaceAfter=2)
    sub = ParagraphStyle('S', fontSize=12, fontName='Helvetica',
                         textColor=MUTED, alignment=TA_CENTER, spaceAfter=8)
    h = ParagraphStyle('H', fontSize=11, fontName='Helvetica-Bold',
                       textColor=ACCENT, spaceBefore=8, spaceAfter=3)
    body = ParagraphStyle('B', parent=styles['Normal'], fontSize=9.5,
                          leading=13)
    foot = ParagraphStyle('F', parent=styles['Normal'], fontSize=8,
                          textColor=MUTED, leading=11, spaceBefore=10)

    story = [Paragraph('VYAYAM', title), Paragraph('Session Report', sub)]
    for kind, lines in report_pdf_sections(report):
        if kind == 'header':
            for line in lines:
                story.append(Paragraph(line, body))
            story.append(HRFlowable(width='100%', thickness=1, color=ACCENT,
                                    spaceBefore=6, spaceAfter=2))
        elif kind == 'exercise':
            story.append(Paragraph(lines[0], h))
            rows = [[Paragraph(l, body)] for l in lines[1:]]
            if rows:
                t = Table(rows, colWidths=[None])
                t.setStyle(TableStyle([
                    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, ROW_ALT]),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(t)
        elif kind == 'footer':
            story.append(HRFlowable(width='100%', thickness=0.5, color=MUTED,
                                    spaceBefore=10, spaceAfter=2))
            for line in lines:
                story.append(Paragraph(line, foot))
        else:
            story.append(Paragraph(_SECTION_TITLES.get(kind, kind.title()), h))
            for line in lines:
                story.append(Paragraph(line, body))
        story.append(Spacer(1, 2))

    doc.build(story)
    buffer.seek(0)
    return buffer


def pdf_filename(report_obj):
    """report_<date>_<patient-first-name>.pdf (spec'd shape)."""
    header = (report_obj.report_json or {}).get('header') or {}
    first = (header.get('patient_name') or 'patient').split()[0].lower()
    safe = ''.join(ch for ch in first if ch.isalnum()) or 'patient'
    return f"report_{report_obj.report_date:%Y%m%d}_{safe}.pdf"
