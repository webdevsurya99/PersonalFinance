import io
import datetime
from typing import List
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.models import Transaction, User

class NumberedCanvas:
    """Canvas for adding page numbers and running header/footer."""
    pass

def generate_pdf_statement(transactions: List[Transaction], user: User, start_date: datetime.date, end_date: datetime.date) -> io.BytesIO:
    """
    Generate an executive PDF Statement of Accounts using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=15
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=12,
        spaceAfter=8
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155")
    )

    cell_bold_style = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )

    cell_income_style = ParagraphStyle(
        'TableCellIncome',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#059669")
    )

    cell_expense_style = ParagraphStyle(
        'TableCellExpense',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#DC2626")
    )

    # 1. Header Banner
    story.append(Paragraph("Personal Financial Statement", title_style))
    story.append(Paragraph(
        f"<b>Account Holder:</b> {user.full_name} ({user.email}) &nbsp;|&nbsp; "
        f"<b>Period:</b> {start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')} &nbsp;|&nbsp; "
        f"<b>Generated:</b> {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}",
        subtitle_style
    ))

    # 2. Financial Summary KPIs
    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    net_savings = total_income - total_expense

    kpi_data = [
        [
            Paragraph("<b>Total Income</b>", cell_style),
            Paragraph("<b>Total Expenses</b>", cell_style),
            Paragraph("<b>Net Savings</b>", cell_style),
            Paragraph("<b>Transactions</b>", cell_style)
        ],
        [
            Paragraph(f"<font size='12' color='#059669'><b>{user.currency_symbol} {total_income:,.2f}</b></font>", cell_style),
            Paragraph(f"<font size='12' color='#DC2626'><b>{user.currency_symbol} {total_expense:,.2f}</b></font>", cell_style),
            Paragraph(
                f"<font size='12' color='{'#059669' if net_savings >= 0 else '#DC2626'}'><b>{user.currency_symbol} {net_savings:,.2f}</b></font>", 
                cell_style
            ),
            Paragraph(f"<font size='12' color='#1E293B'><b>{len(transactions)}</b></font>", cell_style)
        ]
    ]

    kpi_table = Table(kpi_data, colWidths=[130, 130, 130, 130])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 15))

    # 3. Transaction Details
    story.append(Paragraph("Transaction Breakdown", h2_style))

    table_headers = [
        Paragraph("<b>Date</b>", cell_bold_style),
        Paragraph("<b>Type</b>", cell_bold_style),
        Paragraph("<b>Category</b>", cell_bold_style),
        Paragraph("<b>Account / Card</b>", cell_bold_style),
        Paragraph("<b>Trip / Tag</b>", cell_bold_style),
        Paragraph("<b>Amount</b>", cell_bold_style)
    ]
    table_data = [table_headers]

    sorted_txns = sorted(transactions, key=lambda x: x.date, reverse=True)

    for t in sorted_txns:
        source = "—"
        if t.bank_account:
            source = f"{t.bank_account.bank_name} (••{t.bank_account.account_number_last4})"
        elif t.credit_card:
            source = f"{t.credit_card.card_name} (••{t.credit_card.last_4_digits})"

        cat_str = f"{t.category.icon} {t.category.name}" if t.category else "Uncategorized"
        
        trip_tag_parts = []
        if t.trip:
            trip_tag_parts.append(f"Trip: {t.trip.name}")
        if t.tag:
            trip_tag_parts.append(t.tag)
        trip_tag_str = ", ".join(trip_tag_parts) if trip_tag_parts else "—"

        amt_str = f"{'+' if t.type == 'income' else '-'} {user.currency_symbol} {t.amount:,.2f}"
        amt_p = Paragraph(amt_str, cell_income_style if t.type == "income" else cell_expense_style)

        table_data.append([
            Paragraph(t.date.strftime("%d %b %Y"), cell_style),
            Paragraph(t.type.upper(), cell_income_style if t.type == "income" else cell_expense_style),
            Paragraph(cat_str, cell_style),
            Paragraph(source, cell_style),
            Paragraph(trip_tag_str, cell_style),
            amt_p
        ])

    txn_table = Table(table_data, colWidths=[70, 50, 110, 130, 90, 75])
    
    # Table styling with alternating rows
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 1), (-1, -1), 5),
    ]

    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F8FAFC")))

    txn_table.setStyle(TableStyle(t_style))
    story.append(txn_table)

    # Footer note
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "<i>Note: This is an automatically generated personal finance statement from FinMinimal. All calculations are indicative.</i>",
        subtitle_style
    ))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
