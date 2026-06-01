"""PDF report generation for therapist progress reports."""

from collections import Counter, defaultdict
from datetime import timedelta
from io import BytesIO

from django.core.files.base import ContentFile
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import SessionLog, TherapistMessage

SAGE = colors.HexColor('#7BA087')
INK = colors.HexColor('#1F2937')
MUTED = colors.HexColor('#6B7280')
LINE = colors.HexColor('#E5E7EB')

DIFFICULTY_LABEL = {
    'easy': 'Easy',
    'right': 'Just right',
    'hard': 'Hard',
    'too_hard': 'Too hard',
}


def _styles():
    base = getSampleStyleSheet()
    return {
        'h1': ParagraphStyle(
            'h1', parent=base['Heading1'], fontSize=22, textColor=SAGE,
            leading=24, spaceAfter=2,
        ),
        'h2': ParagraphStyle(
            'h2', parent=base['Heading2'], fontSize=12, textColor=INK,
            leading=14, spaceBefore=12, spaceAfter=4,
        ),
        'body': ParagraphStyle(
            'body', parent=base['BodyText'], fontSize=10, textColor=INK,
            leading=13,
        ),
        'muted': ParagraphStyle(
            'muted', parent=base['BodyText'], fontSize=9, textColor=MUTED,
            leading=11,
        ),
        'small': ParagraphStyle(
            'small', parent=base['BodyText'], fontSize=8, textColor=MUTED,
            leading=10,
        ),
    }


def _most_common(values):
    cleaned = [v for v in values if v]
    if not cleaned:
        return None
    return Counter(cleaned).most_common(1)[0][0]


def _fmt_time(dt):
    """Portable 12-hour time like '8:30am' / '12:05pm'."""
    h12 = dt.hour % 12 or 12
    suffix = 'am' if dt.hour < 12 else 'pm'
    return f"{h12}:{dt.minute:02d}{suffix}"


def _local(dt):
    return timezone.localtime(dt) if timezone.is_aware(dt) else dt


def generate_patient_pdf(link, week_start_date, week_end_date):
    """Build a 1-2 page PDF progress report for a patient over a week window.

    Returns a Django ContentFile containing the rendered PDF.
    """
    styles = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title=f"Progress report — {link.display_name}",
    )
    story = []

    # ---- HEADER ----------------------------------------------------------
    therapist = link.therapist
    generated_on = timezone.localdate()
    period_label = (
        f"Week of {week_start_date.strftime('%b %d, %Y')} – "
        f"{week_end_date.strftime('%b %d, %Y')}"
    )
    header_left = [
        Paragraph('VYAYAM', styles['h1']),
        Paragraph(period_label, styles['body']),
    ]
    header_right = [
        Paragraph(f"Generated {generated_on.strftime('%b %d, %Y')}", styles['muted']),
    ]
    header_tbl = Table(
        [[header_left, header_right]],
        colWidths=[4.5 * inch, 2.7 * inch],
    )
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, SAGE),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(header_tbl)

    # ---- PATIENT INFO ----------------------------------------------------
    health = getattr(link, 'health_profile', None)
    affected_side = (
        health.get_affected_side_display()
        if (health and health.affected_side) else '—'
    )
    age_str = f"{link.age}" if link.age else '—'
    condition = link.primary_condition or '—'
    week_n = max(1, link.current_week)

    prescriber_bits = [therapist.full_name]
    if therapist.clinic_name:
        prescriber_bits.append(therapist.clinic_name)
    if therapist.registration_number:
        prescriber_bits.append(f"Reg #{therapist.registration_number}")
    prescriber = ' · '.join(prescriber_bits)

    story.append(Paragraph('Patient', styles['h2']))
    info_rows = [
        ['Name', link.display_name, 'Age', age_str],
        ['Condition', condition, 'Affected side', affected_side],
        ['Program week', f"Week {week_n}", 'Prescribed by', prescriber],
    ]
    info_tbl = Table(
        info_rows,
        colWidths=[1.1 * inch, 2.5 * inch, 1.1 * inch, 2.5 * inch],
    )
    info_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), MUTED),
        ('TEXTCOLOR', (2, 0), (2, -1), MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, LINE),
    ]))
    story.append(info_tbl)

    # ---- WEEK DATA AGGREGATION -------------------------------------------
    sessions = list(
        SessionLog.objects
        .filter(
            link=link,
            started_at__date__gte=week_start_date,
            started_at__date__lte=week_end_date,
        )
        .order_by('started_at')
        .prefetch_related('items')
    )
    sessions_by_day = defaultdict(list)
    for s in sessions:
        sessions_by_day[_local(s.started_at).date()].append(s)

    pain_values = [s.overall_pain for s in sessions if s.overall_pain is not None]
    avg_pain = round(sum(pain_values) / len(pain_values), 1) if pain_values else None

    all_items = [it for s in sessions for it in s.items.all()]
    completed_exercise_count = sum(1 for it in all_items if it.completed_at is not None)
    top_difficulty = _most_common([it.difficulty for it in all_items])

    # ---- SESSION SUMMARY -------------------------------------------------
    story.append(Paragraph('Session summary', styles['h2']))
    summary_rows = [
        ['Sessions completed this week', f"{len(sessions)} of 7"],
        ['Total exercises completed', f"{completed_exercise_count}"],
        ['Average pain reported',
         f"{avg_pain} / 10" if avg_pain is not None else '—'],
        ['Most reported difficulty',
         DIFFICULTY_LABEL.get(top_difficulty, '—') if top_difficulty else '—'],
    ]
    sum_tbl = Table(summary_rows, colWidths=[3.0 * inch, 4.2 * inch])
    sum_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, LINE),
    ]))
    story.append(sum_tbl)

    # ---- COMPLIANCE TABLE ------------------------------------------------
    story.append(Paragraph('Compliance', styles['h2']))
    days = (week_end_date - week_start_date).days + 1
    comp_rows = [['Day', 'Status', 'Pain']]
    for offset in range(days):
        d = week_start_date + timedelta(days=offset)
        day_sessions = sessions_by_day.get(d, [])
        day_label = d.strftime('%a %b %d')
        if not day_sessions:
            comp_rows.append([day_label, '✗ Skipped', '—'])
            continue
        chosen = next((s for s in day_sessions if s.completed_at), day_sessions[0])
        when = _fmt_time(_local(chosen.started_at))
        status_str = f"✓ Session at {when}"
        pain_str = (
            f"{chosen.overall_pain}/10" if chosen.overall_pain is not None else '—'
        )
        comp_rows.append([day_label, status_str, pain_str])
    comp_tbl = Table(
        comp_rows,
        colWidths=[1.6 * inch, 3.4 * inch, 2.2 * inch],
    )
    comp_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, SAGE),
        ('LINEBELOW', (0, 1), (-1, -1), 0.3, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(comp_tbl)

    # ---- EXERCISE BREAKDOWN ---------------------------------------------
    story.append(Paragraph('Exercise breakdown', styles['h2']))

    rx = link.prescriptions.order_by('-week_number', '-created_at').first()
    rx_items = list(rx.items.all()) if rx else []

    completion_by_ex = defaultdict(list)
    for it in all_items:
        completion_by_ex[it.exercise_id or ''].append(it)

    breakdown_rows = [[
        'Exercise', 'Prescribed', 'Avg completed', 'Avg pain', 'Most-reported difficulty',
    ]]
    if rx_items:
        for pi in rx_items:
            logs = completion_by_ex.get(pi.exercise_id, [])
            if logs:
                sets_avg = sum(it.sets_completed for it in logs) / len(logs)
                pains = [it.pain for it in logs if it.pain is not None]
                pain_avg = (
                    round(sum(pains) / len(pains), 1) if pains else None
                )
                top = _most_common([it.difficulty for it in logs])
                avg_str = f"{sets_avg:.1f} × {pi.reps}"
                pain_str = f"{pain_avg}/10" if pain_avg is not None else '—'
                diff_str = DIFFICULTY_LABEL.get(top, '—') if top else '—'
            else:
                avg_str = pain_str = diff_str = '—'
            breakdown_rows.append([
                pi.exercise_name,
                f"{pi.sets} × {pi.reps}",
                avg_str,
                pain_str,
                diff_str,
            ])
    else:
        breakdown_rows.append([
            'No active prescription this week.', '', '', '', '',
        ])

    br_tbl = Table(
        breakdown_rows,
        colWidths=[2.3 * inch, 1.0 * inch, 1.1 * inch, 0.9 * inch, 1.9 * inch],
    )
    br_tbl.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, SAGE),
        ('LINEBELOW', (0, 1), (-1, -1), 0.3, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(br_tbl)

    # ---- THERAPIST NOTES ------------------------------------------------
    story.append(Paragraph('Therapist notes', styles['h2']))
    latest_msg = (
        TherapistMessage.objects
        .filter(link=link, sender=therapist.user)
        .order_by('-sent_at')
        .first()
    )
    if latest_msg:
        when_str = _local(latest_msg.sent_at).strftime('%b %d, %Y')
        story.append(Paragraph(
            f"<i>{when_str}</i> — {latest_msg.body}", styles['body'],
        ))
    else:
        story.append(Paragraph("No clinical notes this week.", styles['muted']))

    # ---- DISCLAIMER FOOTER ----------------------------------------------
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "This report is generated automatically from patient-reported data. "
        "It is not a clinical assessment. The supervising physiotherapist has "
        "reviewed and remains responsible for all clinical decisions.",
        styles['small'],
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()

    fname = f"week-{week_start_date.isoformat()}-{link.id}.pdf"
    return ContentFile(pdf_bytes, name=fname)
