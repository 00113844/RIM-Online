from __future__ import annotations

from io import BytesIO

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def tables_to_excel_bytes(tables: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, table in tables.items():
            safe_name = sheet_name[:31]
            table.to_excel(writer, index=False, sheet_name=safe_name)
    buffer.seek(0)
    return buffer.getvalue()


def results_to_pdf_bytes(title: str, blocks: list[str]) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, title)
    y -= 30

    c.setFont("Helvetica", 10)
    for block in blocks:
        for line in block.splitlines():
            if y < 70:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 10)
            c.drawString(50, y, line[:120])
            y -= 14
        y -= 6

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
