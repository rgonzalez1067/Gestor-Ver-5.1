"""Reporte General de Marcas: cada Marca con el detalle de sus RIF (PDF / Excel)."""
import io
from html import escape as esc
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import db, get_current_user
from services.report_header import draw_page_header
from services.rif_formatter import format_rif

router = APIRouter()
MAX_BRANDS = 2000


class BrandReportRequest(BaseModel):
    brand_ids: list[str]
    filters_label: Optional[str] = ""


async def _report_data(ids: list[str]) -> list[dict]:
    brands = await db.brands.find({"brand_id": {"$in": ids}}, {"_id": 0, "brand_id": 1, "name": 1, "group_id": 1}).to_list(None)
    gids = list({b.get("group_id") for b in brands if b.get("group_id")})
    gmap = {g["group_id"]: g["name"] for g in await db.economic_groups.find({"group_id": {"$in": gids}}, {"_id": 0, "group_id": 1, "name": 1}).to_list(None)}
    rifs = await db.clients.find(
        {"marca_id": {"$in": ids}, "is_branch": {"$ne": True}},
        {"_id": 0, "client_id": 1, "marca_id": 1, "rif": 1, "legal_name": 1, "segment": 1, "ejecutivo_propietario": 1}).to_list(None)
    branch_counts = {r["_id"]: r["n"] for r in await db.clients.aggregate([
        {"$match": {"is_branch": True, "parent_id": {"$in": [r["client_id"] for r in rifs]}}},
        {"$group": {"_id": "$parent_id", "n": {"$sum": 1}}}]).to_list(None)}
    by_brand = {}
    for r in rifs:
        by_brand.setdefault(r["marca_id"], []).append({
            "rif": format_rif(r.get("rif", "")), "legal_name": r.get("legal_name") or "",
            "branches": branch_counts.get(r["client_id"], 0) + 1,
            "segment": r.get("segment") or "", "ejecutivo": (r.get("ejecutivo_propietario") or "").strip()})
    out = [{"name": b["name"], "group": gmap.get(b.get("group_id"), ""),
            "rifs": sorted(by_brand.get(b["brand_id"], []), key=lambda x: x["legal_name"].lower())} for b in brands]
    return sorted(out, key=lambda b: b["name"].lower())


def _xlsx(data: list[dict]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Marcas"
    head = ["Marca / Nombre Fantasía", "Grupo Económico", "RIF", "Razón Social", "Sucursales", "Segmento", "Ejecutivo Propietario"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="D97706")
        c.alignment = Alignment(vertical="center")
    for b in data:
        for r in b["rifs"] or [{"rif": "", "legal_name": "Sin RIF asociados", "branches": 0, "segment": "", "ejecutivo": ""}]:
            ws.append([b["name"], b["group"], r["rif"], r["legal_name"], r["branches"], r["segment"], r["ejecutivo"]])
    for col, w in zip("ABCDEFG", (34, 28, 16, 42, 12, 16, 28)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pdf(data: list[dict], filters_label: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ACCENT, DARK = "#d97706", "#92400e"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=26 * mm, bottomMargin=14 * mm, title="Reporte General de Marcas")
    ss = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=15, textColor=colors.HexColor(DARK), leading=18)
    sub = ParagraphStyle("s", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor("#64748b"), leading=12)
    brand_st = ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=10.5, textColor=colors.HexColor(DARK), leading=13)
    cell = ParagraphStyle("c", parent=ss["Normal"], fontSize=8.5, leading=10.5)
    total_rifs = sum(len(b["rifs"]) for b in data)
    total_br = sum(r["branches"] for b in data for r in b["rifs"])
    story = [Paragraph("Reporte General de Marcas", title),
             Paragraph(f"{len(data)} marcas · {total_rifs} RIF · {total_br} sucursales"
                       + (f" · Filtros: {esc(filters_label)}" if filters_label else "")
                       + f" · Emitido {datetime.now(timezone.utc).strftime('%d/%m/%Y')}", sub), Spacer(1, 10)]
    widths = [38 * mm, 88 * mm, 22 * mm, 34 * mm, 60 * mm]
    for b in data:
        head = Paragraph(f"{esc(b['name'])}" + (f"  <font size='8.5' color='#64748b'>· Grupo: {esc(b['group'])}</font>" if b["group"] else ""), brand_st)
        rows = [["RIF", "Razón Social", "Sucursales", "Segmento", "Ejecutivo Propietario"]]
        rows += [[r["rif"], Paragraph(esc(r["legal_name"]), cell), str(r["branches"]), r["segment"] or "—", Paragraph(esc(r["ejecutivo"] or "—"), cell)]
                 for r in b["rifs"]] or [["", Paragraph("Sin RIF asociados", cell), "", "", ""]]
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(ACCENT)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (2, 1), (2, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fffbeb")]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ]))
        block = [head, Spacer(1, 3), t]
        story += ([KeepTogether(block)] if len(rows) < 25 else block) + [Spacer(1, 9)]

    def _decor(canvas, doc_):
        draw_page_header(canvas, doc_, "Reporte General de Marcas")
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.drawRightString(doc_.pagesize[0] - 14 * mm, 8 * mm, f"Página {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_decor, onLaterPages=_decor)
    return buf.getvalue()


@router.post("/marcas/report")
async def brands_report(req: BrandReportRequest, format: str = "pdf", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    ids = list(dict.fromkeys(req.brand_ids or []))
    if not ids:
        raise HTTPException(status_code=400, detail="No hay marcas para el reporte")
    if len(ids) > MAX_BRANDS:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_BRANDS} marcas por reporte")
    data = await _report_data(ids)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if format == "xlsx":
        return StreamingResponse(io.BytesIO(_xlsx(data)),
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": f'attachment; filename="Reporte_Marcas_{stamp}.xlsx"'})
    return StreamingResponse(io.BytesIO(_pdf(data, req.filters_label or "")), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="Reporte_Marcas_{stamp}.pdf"'})
