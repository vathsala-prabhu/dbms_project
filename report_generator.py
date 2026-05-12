from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import Flowable
import io
from datetime import datetime

# ── Professional Color Palette ────────────────────────────────────────────────
C_WHITE       = colors.white
C_BLACK       = colors.HexColor('#1a1a1a')
C_NAVY        = colors.HexColor('#0d2b4e')       # Header / accent
C_NAVY_LIGHT  = colors.HexColor('#1a4a8a')
C_BLUE_ACCENT = colors.HexColor('#2563eb')
C_TEAL        = colors.HexColor('#0e7490')
C_GRAY_DARK   = colors.HexColor('#374151')
C_GRAY        = colors.HexColor('#6b7280')
C_GRAY_LIGHT  = colors.HexColor('#f3f4f6')
C_GRAY_MID    = colors.HexColor('#e5e7eb')
C_RULE        = colors.HexColor('#d1d5db')

# Risk colors – professional, not neon
C_RED_BG      = colors.HexColor('#fef2f2')
C_RED_BORDER  = colors.HexColor('#ef4444')
C_RED_TEXT    = colors.HexColor('#b91c1c')
C_AMBER_BG    = colors.HexColor('#fffbeb')
C_AMBER_BORDER= colors.HexColor('#f59e0b')
C_AMBER_TEXT  = colors.HexColor('#92400e')
C_GREEN_BG    = colors.HexColor('#f0fdf4')
C_GREEN_BORDER= colors.HexColor('#22c55e')
C_GREEN_TEXT  = colors.HexColor('#15803d')
C_BLUE_BG     = colors.HexColor('#eff6ff')
C_BLUE_TEXT   = colors.HexColor('#1e40af')

RISK_PALETTE = {
    'High':          (C_RED_BG,    C_RED_BORDER,    C_RED_TEXT),
    'Medium':        (C_AMBER_BG,  C_AMBER_BORDER,  C_AMBER_TEXT),
    'Low':           (C_GREEN_BG,  C_GREEN_BORDER,  C_GREEN_TEXT),
    'None Detected': (C_BLUE_BG,   C_RULE,          C_BLUE_TEXT),
}


# ── Custom Flowables ──────────────────────────────────────────────────────────
class HeaderRule(Flowable):
    """A thick colored rule to separate major sections."""
    def __init__(self, color=C_NAVY, thickness=3, width_pct=1.0):
        Flowable.__init__(self)
        self.color = color
        self.thickness = thickness
        self.width_pct = width_pct

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width * self.width_pct, self.thickness, fill=1, stroke=0)

    def wrap(self, availW, availH):
        self.width = availW
        return availW, self.thickness


class SectionTitle(Flowable):
    """Professional section title with left accent bar."""
    def __init__(self, number, title, height=9*mm):
        Flowable.__init__(self)
        self.number = number
        self.title  = title
        self.height = height

    def draw(self):
        # Left accent bar
        self.canv.setFillColor(C_NAVY)
        self.canv.rect(0, 0, 3, self.height, fill=1, stroke=0)
        # Light background
        self.canv.setFillColor(C_GRAY_LIGHT)
        self.canv.rect(3, 0, self.width - 3, self.height, fill=1, stroke=0)
        # Section number
        self.canv.setFillColor(C_NAVY_LIGHT)
        self.canv.setFont('Helvetica-Bold', 8)
        self.canv.drawString(8, self.height/2 + 1, self.number)
        # Title
        self.canv.setFillColor(C_NAVY)
        self.canv.setFont('Helvetica-Bold', 10)
        self.canv.drawString(22, self.height/2 - 4, self.title)

    def wrap(self, availW, availH):
        self.width = availW
        return availW, self.height


class BaseCompositionBar(Flowable):
    """Clean segmented bar for base composition."""
    def __init__(self, base_counts, total, height=6*mm):
        Flowable.__init__(self)
        self.base_counts = base_counts
        self.total       = total
        self.height      = height

    def draw(self):
        base_colors = {
            'A': colors.HexColor('#3b82f6'),
            'T': colors.HexColor('#f59e0b'),
            'C': colors.HexColor('#10b981'),
            'G': colors.HexColor('#8b5cf6'),
        }
        x = 0
        radius = 2
        for base, cnt in self.base_counts.items():
            frac  = cnt / self.total if self.total else 0
            seg_w = frac * self.width
            self.canv.setFillColor(base_colors.get(base, C_GRAY))
            self.canv.rect(x, 0, seg_w, self.height, fill=1, stroke=0)
            if seg_w > 14*mm:
                self.canv.setFillColor(C_WHITE)
                self.canv.setFont('Helvetica-Bold', 7)
                lbl = f"{base}  {frac*100:.1f}%"
                self.canv.drawCentredString(x + seg_w/2, self.height/2 - 3, lbl)
            x += seg_w

    def wrap(self, availW, availH):
        self.width = availW
        return availW, self.height


# ── Page Template ─────────────────────────────────────────────────────────────
def on_page(canvas, doc, patient_name='', report_date=''):
    canvas.saveState()
    W, H = A4

    # ── Top header strip ──
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, H - 20*mm, W, 20*mm, fill=1, stroke=0)

    # Logo area / org name
    canvas.setFillColor(C_WHITE)
    canvas.setFont('Helvetica-Bold', 13)
    canvas.drawString(15*mm, H - 11*mm, 'DNA MUTATION ANALYSIS REPORT')

    canvas.setFillColor(colors.HexColor('#93c5fd'))
    canvas.setFont('Helvetica', 8)
    canvas.drawString(15*mm, H - 16*mm, 'Confidential Genetic Analysis Document')

    # Right side: page info
    canvas.setFillColor(C_WHITE)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(W - 15*mm, H - 11*mm, f'Page {doc.page}')
    canvas.setFillColor(colors.HexColor('#93c5fd'))
    canvas.setFont('Helvetica', 7)
    canvas.drawRightString(W - 15*mm, H - 16*mm, report_date)

    # Thin accent line under header
    canvas.setFillColor(colors.HexColor('#2563eb'))
    canvas.rect(0, H - 20.5*mm, W, 0.5*mm, fill=1, stroke=0)

    # ── Footer ──
    canvas.setFillColor(C_GRAY_LIGHT)
    canvas.rect(0, 0, W, 12*mm, fill=1, stroke=0)
    canvas.setStrokeColor(C_RULE)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 12*mm, W - 15*mm, 12*mm)

    canvas.setFillColor(C_GRAY)
    canvas.setFont('Helvetica', 6.5)
    canvas.drawString(15*mm, 4.5*mm,
        'DISCLAIMER: This report is for informational purposes only and does not constitute medical advice. '
        'Results must be interpreted by a qualified healthcare professional.')
    canvas.drawRightString(W - 15*mm, 4.5*mm, 'DNA Analyzer  |  Confidential')

    canvas.restoreState()


# ── Style Sheet ───────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base['Normal'], **kw)

    return {
        'report_title': ps('rpt_title',
            fontName='Helvetica-Bold', fontSize=24,
            textColor=C_NAVY, alignment=TA_CENTER,
            spaceAfter=4, spaceBefore=4),

        'report_subtitle': ps('rpt_sub',
            fontName='Helvetica', fontSize=10,
            textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=12),

        'patient_label': ps('pt_label',
            fontName='Helvetica-Bold', fontSize=7.5,
            textColor=C_GRAY, spaceAfter=2,
            leading=10),

        'patient_value': ps('pt_val',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=C_NAVY, spaceAfter=2,
            leading=14),

        'body': ps('body',
            fontName='Helvetica', fontSize=9.5,
            textColor=C_GRAY_DARK, leading=15),

        'body_small': ps('body_sm',
            fontName='Helvetica', fontSize=8.5,
            textColor=C_GRAY, leading=13),

        'table_header': ps('tbl_hdr',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=C_WHITE, alignment=TA_CENTER),

        'table_cell': ps('tbl_cell',
            fontName='Helvetica', fontSize=8.5,
            textColor=C_GRAY_DARK, leading=12),

        'table_cell_center': ps('tbl_cell_c',
            fontName='Helvetica', fontSize=8.5,
            textColor=C_GRAY_DARK, alignment=TA_CENTER),

        'stat_number': ps('stat_num',
            fontName='Helvetica-Bold', fontSize=18,
            textColor=C_NAVY, alignment=TA_CENTER),

        'stat_label': ps('stat_lbl',
            fontName='Helvetica', fontSize=7.5,
            textColor=C_GRAY, alignment=TA_CENTER),

        'risk_badge_high':   ps('rb_h', fontName='Helvetica-Bold', fontSize=9,
                                textColor=C_RED_TEXT, alignment=TA_CENTER),
        'risk_badge_medium': ps('rb_m', fontName='Helvetica-Bold', fontSize=9,
                                textColor=C_AMBER_TEXT, alignment=TA_CENTER),
        'risk_badge_low':    ps('rb_l', fontName='Helvetica-Bold', fontSize=9,
                                textColor=C_GREEN_TEXT, alignment=TA_CENTER),
        'risk_badge_none':   ps('rb_n', fontName='Helvetica-Bold', fontSize=9,
                                textColor=C_BLUE_TEXT, alignment=TA_CENTER),

        'match_disease': ps('dis',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=C_NAVY, spaceAfter=2),

        'match_meta': ps('meta',
            fontName='Helvetica', fontSize=8,
            textColor=C_GRAY, leading=12),

        'match_desc': ps('desc',
            fontName='Helvetica', fontSize=9,
            textColor=C_GRAY_DARK, leading=14),

        'recommendation': ps('rec',
            fontName='Helvetica', fontSize=9.5,
            textColor=C_GRAY_DARK, leading=15, alignment=TA_JUSTIFY),

        'disclaimer': ps('disc',
            fontName='Helvetica', fontSize=7.5,
            textColor=C_GRAY, leading=11, alignment=TA_JUSTIFY),

        'sequence_mono': ps('seq_mono',
            fontName='Courier', fontSize=7.5,
            textColor=C_GRAY_DARK, leading=11),

        'gc_interpretation': ps('gc_interp',
            fontName='Helvetica', fontSize=9,
            textColor=C_GRAY_DARK, leading=14, alignment=TA_JUSTIFY),
    }


def risk_badge_style(styles, level):
    return styles.get({
        'High':          'risk_badge_high',
        'Medium':        'risk_badge_medium',
        'Low':           'risk_badge_low',
        'None Detected': 'risk_badge_none',
    }.get(level, 'risk_badge_none'))


# ── Main Generator ────────────────────────────────────────────────────────────
def generate_pdf_report(data: dict) -> bytes:
    buffer = io.BytesIO()
    W_page, H_page = A4
    left_margin = right_margin = 18*mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=24*mm,
        bottomMargin=18*mm,
        leftMargin=left_margin,
        rightMargin=right_margin,
    )

    styles = make_styles()
    story  = []
    W      = W_page - left_margin - right_margin   # usable content width

    patient_name  = data.get('patient_name', 'Unknown Patient')
    seq_stats     = data.get('sequence_stats', {})
    matches       = data.get('matches', [])
    risk_summary  = data.get('risk_summary', {})
    overall_risk  = risk_summary.get('overall_risk', 'Unknown')
    sequence_snip = data.get('sequence_snippet', '')
    report_date   = datetime.now().strftime('%B %d, %Y')
    report_time   = datetime.now().strftime('%H:%M')

    # Bind page callback with metadata
    def page_cb(canvas, doc):
        on_page(canvas, doc, patient_name=patient_name,
                report_date=f'{report_date}  {report_time}')

    # ── Cover / Patient Summary ───────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))

    # Report title block
    story.append(Paragraph('Genetic Mutation Analysis Report', styles['report_title']))
    story.append(Paragraph(
        f'Prepared for: <b>{patient_name}</b>  &nbsp;|&nbsp;  {report_date}',
        styles['report_subtitle']
    ))
    story.append(HeaderRule(C_NAVY, thickness=2))
    story.append(Spacer(1, 5*mm))

    # Patient info + overall risk — two-column layout
    risk_bg, risk_border, risk_text = RISK_PALETTE.get(overall_risk, RISK_PALETTE['None Detected'])

    info_left = [
        [Paragraph('PATIENT NAME', styles['patient_label'])],
        [Paragraph(patient_name,   styles['patient_value'])],
        [Spacer(1, 3*mm)],
        [Paragraph('REPORT DATE',  styles['patient_label'])],
        [Paragraph(report_date,    styles['patient_value'])],
    ]
    info_left_tbl = Table(info_left, colWidths=[W * 0.55])
    info_left_tbl.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
    ]))

    risk_label = overall_risk.upper() if overall_risk != 'None Detected' else 'NO RISK DETECTED'
    risk_card_data = [
        [Paragraph('OVERALL RISK ASSESSMENT', styles['patient_label'])],
        [Paragraph(f'<b>{risk_label}</b>',
                   ParagraphStyle('rk_big', parent=styles['patient_value'],
                                  textColor=risk_text, fontSize=15, alignment=TA_CENTER))],
        [Paragraph(f"{len(matches)} variant{'s' if len(matches) != 1 else ''} detected",
                   ParagraphStyle('rk_sub', parent=styles['body_small'], alignment=TA_CENTER))],
    ]
    risk_card_tbl = Table(risk_card_data, colWidths=[W * 0.38])
    risk_card_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), risk_bg),
        ('BOX',           (0,0), (-1,-1), 1.5, risk_border),
        ('ROUNDEDCORNERS',(0,0), (-1,-1), 4),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))

    overview_row = [[info_left_tbl, risk_card_tbl]]
    overview_tbl = Table(overview_row, colWidths=[W * 0.60, W * 0.40])
    overview_tbl.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(overview_tbl)
    story.append(Spacer(1, 5*mm))

    # Clinical recommendation banner
    rec_text = risk_summary.get('recommendation', '')
    rec_bg, rec_border, _ = RISK_PALETTE.get(overall_risk, RISK_PALETTE['None Detected'])
    rec_data = [[
        Paragraph(f'<b>Clinical Recommendation</b>', styles['patient_label']),
    ],[
        Paragraph(rec_text, styles['recommendation']),
    ]]
    rec_tbl = Table(rec_data, colWidths=[W])
    rec_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), rec_bg),
        ('BOX',           (0,0), (-1,-1), 1, rec_border),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
    ]))
    story.append(rec_tbl)
    story.append(Spacer(1, 7*mm))

    # ── Section 1: Sequence Statistics ───────────────────────────────────────
    story.append(SectionTitle('01', 'SEQUENCE STATISTICS'))
    story.append(Spacer(1, 4*mm))

    bc    = seq_stats.get('base_counts', {})
    total = seq_stats.get('length', 1) or 1
    gc    = seq_stats.get('gc_content', 0)
    at    = round(100 - gc, 2)

    # Key metrics row
    metrics = [
        (f"{seq_stats.get('length', 0):,} bp", 'Total Length'),
        (f"{gc}%", 'GC Content'),
        (f"{at}%", 'AT Content'),
        (str(len(matches)), 'Mutations Found'),
    ]
    metric_data = [[Paragraph(v, styles['stat_number']) for v, _ in metrics],
                   [Paragraph(l, styles['stat_label'])  for _, l in metrics]]

    metric_tbl = Table(metric_data, colWidths=[W/4]*4)
    metric_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C_GRAY_LIGHT),
        ('BOX',           (0,0), (-1,-1), 0.5, C_RULE),
        ('INNERGRID',     (0,0), (-1,-1), 0.5, C_RULE),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(metric_tbl)
    story.append(Spacer(1, 4*mm))

    # Base counts table
    bc_header = [Paragraph(b, styles['table_header']) for b in
                 ['Nucleotide', 'Count', 'Percentage', 'Notes']]
    bc_notes = {
        'A': 'Adenine — pairs with Thymine',
        'T': 'Thymine — pairs with Adenine',
        'C': 'Cytosine — pairs with Guanine',
        'G': 'Guanine — pairs with Cytosine',
    }
    bc_rows = [bc_header]
    for base in ['A', 'T', 'C', 'G']:
        cnt = bc.get(base, 0)
        pct = f"{cnt / total * 100:.2f}%"
        bc_rows.append([
            Paragraph(f'<b>{base}</b> — {bc_notes[base][:18]}', styles['table_cell']),
            Paragraph(f'{cnt:,}', styles['table_cell_center']),
            Paragraph(pct, styles['table_cell_center']),
            Paragraph(bc_notes[base], styles['body_small']),
        ])

    bc_tbl = Table(bc_rows, colWidths=[W*0.30, W*0.15, W*0.15, W*0.40], repeatRows=1)
    bc_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
        ('BACKGROUND',    (0,1), (-1,-1), C_WHITE),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_GRAY_LIGHT]),
        ('BOX',           (0,0), (-1,-1), 0.5, C_RULE),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, C_RULE),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('ALIGN',         (1,0), (2,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(bc_tbl)
    story.append(Spacer(1, 3*mm))

    # Base composition bar
    story.append(Paragraph('Base Composition Distribution', styles['patient_label']))
    story.append(Spacer(1, 1*mm))
    story.append(BaseCompositionBar(bc, total, height=8*mm))
    story.append(Spacer(1, 2*mm))

    # Legend
    bar_colors = {'A': '#3b82f6', 'T': '#f59e0b', 'C': '#10b981', 'G': '#8b5cf6'}
    legend_cells = [Paragraph(
        f'<font color="{bar_colors[b]}">&#9632;</font>  {b} – {["Adenine","Thymine","Cytosine","Guanine"][i]}',
        styles['body_small']
    ) for i, b in enumerate(['A', 'T', 'C', 'G'])]
    leg_tbl = Table([legend_cells], colWidths=[W/4]*4)
    leg_tbl.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(leg_tbl)

    # Sequence preview
    if sequence_snip:
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph('Sequence Preview (first 120 bp)', styles['patient_label']))
        story.append(Spacer(1, 1*mm))
        snip_data = [[Paragraph(sequence_snip[:120], styles['sequence_mono'])]]
        snip_tbl = Table(snip_data, colWidths=[W])
        snip_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), C_GRAY_LIGHT),
            ('BOX',           (0,0), (-1,-1), 0.5, C_RULE),
            ('TOPPADDING',    (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ]))
        story.append(snip_tbl)

    story.append(Spacer(1, 7*mm))

    # ── Section 2: Risk Assessment Summary ───────────────────────────────────
    story.append(SectionTitle('02', 'RISK ASSESSMENT SUMMARY'))
    story.append(Spacer(1, 4*mm))

    high_c   = risk_summary.get('high_risk_count', 0)
    medium_c = risk_summary.get('medium_risk_count', 0)
    low_c    = risk_summary.get('low_risk_count', 0)

    risk_counts = [
        (str(high_c),   'High Risk Variants',   C_RED_BG,    C_RED_BORDER,    C_RED_TEXT),
        (str(medium_c), 'Medium Risk Variants',  C_AMBER_BG,  C_AMBER_BORDER,  C_AMBER_TEXT),
        (str(low_c),    'Low Risk Variants',     C_GREEN_BG,  C_GREEN_BORDER,  C_GREEN_TEXT),
        (str(len(matches)), 'Total Variants',    C_BLUE_BG,   C_BLUE_TEXT,     C_BLUE_TEXT),
    ]

    rc_data = []
    rc_row_vals = []
    rc_row_labels = []
    for val, lbl, bg, brd, txt in risk_counts:
        rc_row_vals.append(
            Paragraph(f'<b>{val}</b>',
                      ParagraphStyle(f'rc_{lbl}', parent=styles['stat_number'],
                                     textColor=txt, fontSize=20))
        )
        rc_row_labels.append(Paragraph(lbl, styles['stat_label']))

    rc_tbl = Table([rc_row_vals, rc_row_labels], colWidths=[W/4]*4)
    ts = [
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('BOX',           (0,0), (-1,-1), 0.5, C_RULE),
        ('INNERGRID',     (0,0), (-1,-1), 0.5, C_RULE),
    ]
    for i, (_, _, bg, brd, _) in enumerate(risk_counts):
        ts.append(('BACKGROUND', (i,0), (i,1), bg))
    rc_tbl.setStyle(TableStyle(ts))
    story.append(rc_tbl)
    story.append(Spacer(1, 7*mm))

    # ── Section 3: Detected Mutations ────────────────────────────────────────
    story.append(SectionTitle('03', f'DETECTED MUTATIONS  ({len(matches)} found)'))
    story.append(Spacer(1, 4*mm))

    if not matches:
        no_match_data = [[Paragraph(
            'No known disease-associated mutations were detected in this sequence. '
            'This result does not exclude all possible pathogenic variants — variants '
            'not present in the reference database cannot be detected.',
            styles['body']
        )]]
        no_match_tbl = Table(no_match_data, colWidths=[W])
        no_match_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), C_GREEN_BG),
            ('BOX',           (0,0), (-1,-1), 1, C_GREEN_BORDER),
            ('TOPPADDING',    (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING',   (0,0), (-1,-1), 12),
            ('RIGHTPADDING',  (0,0), (-1,-1), 12),
        ]))
        story.append(no_match_tbl)
    else:
        # Summary table
        hdr_row = [
            Paragraph(h, styles['table_header']) for h in
            ['#', 'Disease / Condition', 'Gene', 'SNP ID', 'Risk Level', 'Strand', 'Position']
        ]
        tbl_data = [hdr_row]
        for i, m in enumerate(matches, 1):
            rl = m.get('risk_level', 'Low')
            _, _, txt_col = RISK_PALETTE.get(rl, RISK_PALETTE['None Detected'])
            rl_para = Paragraph(
                f'<b>{rl}</b>',
                ParagraphStyle(f'rl_{i}', parent=styles['table_cell_center'], textColor=txt_col)
            )
            tbl_data.append([
                Paragraph(str(i), styles['table_cell_center']),
                Paragraph(m.get('disease', ''), styles['table_cell']),
                Paragraph(m.get('gene', ''), styles['table_cell']),
                Paragraph(m.get('snp_id', ''), styles['table_cell']),
                rl_para,
                Paragraph(m.get('strand', ''), styles['body_small']),
                Paragraph(str(m.get('position', '-')), styles['table_cell_center']),
            ])

        col_ws = [W*0.04, W*0.26, W*0.10, W*0.12, W*0.12, W*0.20, W*0.16]
        mut_tbl = Table(tbl_data, colWidths=col_ws, repeatRows=1)
        ts2 = [
            ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_GRAY_LIGHT]),
            ('BOX',           (0,0), (-1,-1), 0.5, C_RULE),
            ('INNERGRID',     (0,0), (-1,-1), 0.3, C_RULE),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 5),
            ('ALIGN',         (0,0), (0,-1), 'CENTER'),
            ('ALIGN',         (4,0), (6,-1), 'CENTER'),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ]
        # Color code risk cells
        for i, m in enumerate(matches, 1):
            rl = m.get('risk_level', 'Low')
            bg, _, _ = RISK_PALETTE.get(rl, RISK_PALETTE['None Detected'])
            ts2.append(('BACKGROUND', (4,i), (4,i), bg))
        mut_tbl.setStyle(TableStyle(ts2))
        story.append(mut_tbl)
        story.append(Spacer(1, 6*mm))

        # Detailed variant cards
        story.append(Paragraph('Detailed Variant Profiles', styles['patient_label']))
        story.append(Spacer(1, 3*mm))

        for i, m in enumerate(matches, 1):
            rl = m.get('risk_level', 'Low')
            card_bg, card_border, card_txt = RISK_PALETTE.get(rl, RISK_PALETTE['None Detected'])

            header_row = [[
                Paragraph(f"{i}.  {m.get('disease', 'Unknown')}", styles['match_disease']),
                Paragraph(
                    f'<b>{rl} RISK</b>',
                    ParagraphStyle(f'cd_{i}', parent=styles['risk_badge_' + rl.lower()
                                   if rl.lower() in ('high','medium','low') else 'none'],
                                   textColor=card_txt, alignment=TA_RIGHT, fontSize=10)
                ),
            ]]
            meta_row = [[
                Paragraph(
                    f"Gene: <b>{m.get('gene','N/A')}</b>&nbsp;&nbsp;&nbsp;"
                    f"SNP ID: <b>{m.get('snp_id','N/A')}</b>&nbsp;&nbsp;&nbsp;"
                    f"Strand: <b>{m.get('strand','N/A')}</b>&nbsp;&nbsp;&nbsp;"
                    f"Position: <b>{m.get('position','-')}</b>",
                    styles['match_meta']
                ),
                Paragraph('', styles['body_small']),
            ]]
            desc_row = [[
                Paragraph(m.get('description', 'No description available.'), styles['match_desc']),
                Paragraph('', styles['body_small']),
            ]]

            card_data = header_row + meta_row + desc_row
            card_tbl = Table(card_data, colWidths=[W * 0.78, W * 0.22])
            card_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), card_bg),
                ('BOX',           (0,0), (-1,-1), 1, card_border),
                ('LINEBELOW',     (0,0), (-1,0), 0.5, card_border),
                ('SPAN',          (0,2), (1,2)),
                ('TOPPADDING',    (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING',   (0,0), (-1,-1), 10),
                ('RIGHTPADDING',  (0,0), (-1,-1), 10),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN',         (1,0), (1,0), 'RIGHT'),
            ]))
            story.append(KeepTogether([card_tbl, Spacer(1, 3*mm)]))

    story.append(Spacer(1, 7*mm))

    # ── Section 4: GC Content Analysis ───────────────────────────────────────
    story.append(SectionTitle('04', 'GC CONTENT ANALYSIS'))
    story.append(Spacer(1, 4*mm))

    if gc < 35:
        gc_interp = ('Low GC content (< 35%). This sequence falls in the AT-rich range, '
                     'which may indicate a regulatory region, repetitive element, or '
                     'non-coding region. AT-rich sequences generally have lower melting '
                     'temperatures and may require lower annealing temperatures for PCR.')
    elif gc < 45:
        gc_interp = ('Moderately low GC content (35–45%). This is within normal range for '
                     'some mammalian genomic regions. Standard PCR protocols are appropriate '
                     'for amplification of this sequence.')
    elif gc <= 65:
        gc_interp = ('Normal GC content (45–65%). This falls within the typical range for '
                     'human coding sequences, and is associated with a stable double-stranded '
                     'DNA structure. Standard laboratory protocols apply.')
    else:
        gc_interp = ('High GC content (> 65%). GC-rich sequences may form stable secondary '
                     'structures such as G-quadruplexes and hairpins. Consider high-GC '
                     'PCR protocols and additives such as DMSO when amplifying this region.')

    gc_data = [
        [
            Paragraph('GC %', styles['table_header']),
            Paragraph('AT %', styles['table_header']),
            Paragraph('Interpretation', styles['table_header']),
        ],
        [
            Paragraph(f'<b>{gc}%</b>', ParagraphStyle('gcv', parent=styles['stat_number'],
                                                       fontSize=16, textColor=C_TEAL)),
            Paragraph(f'<b>{at}%</b>', ParagraphStyle('atv', parent=styles['stat_number'],
                                                       fontSize=16, textColor=C_NAVY_LIGHT)),
            Paragraph(gc_interp, styles['gc_interpretation']),
        ],
    ]
    gc_tbl = Table(gc_data, colWidths=[W*0.12, W*0.12, W*0.76])
    gc_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
        ('BACKGROUND',    (0,1), (1,1), C_GRAY_LIGHT),
        ('BACKGROUND',    (2,1), (2,1), C_WHITE),
        ('BOX',           (0,0), (-1,-1), 0.5, C_RULE),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, C_RULE),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('ALIGN',         (0,0), (1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(gc_tbl)
    story.append(Spacer(1, 8*mm))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_RULE, spaceAfter=4))
    disclaimer_text = (
        '<b>DISCLAIMER:</b> This report has been generated by an automated DNA analysis system '
        'for informational and research purposes only. It does not constitute medical advice, '
        'diagnosis, or treatment recommendation. All results should be reviewed and interpreted '
        'by a qualified healthcare professional or licensed genetic counselor. Variants not '
        'present in the reference mutation database cannot be detected. The possibility of '
        'false positive and false negative results exists. Anthropic and the developers of '
        'this tool accept no liability for clinical decisions made based on this report.'
    )
    story.append(Paragraph(disclaimer_text, styles['disclaimer']))

    doc.build(story, onFirstPage=page_cb, onLaterPages=page_cb)
    return buffer.getvalue()