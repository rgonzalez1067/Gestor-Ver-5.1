"""Reporte de Seguimiento de Proyectos (Comerciales e Implementadores): filtros + PDF / Excel."""
import io
from datetime import datetime, timezone
from html import escape
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from config import db, get_current_user

router = APIRouter(tags=["projects-followup-report"])

FINISHED = {"Culminado", "Implementado parcial", "Anulado", "Cancelado", "Finalizado"}
TYPE_LABEL = {"VPOS": "VPOS", "MPOS": "MPOS", "GATEWAY": "Payment Gateway", "LINK": "Link de Pago"}
LEVEL_LABEL = {"critico": "Retraso Crítico", "medio": "Retraso Medio", "al_dia": "Al Día"}
MOTIVO_LABEL = {"CLIENTE": "Cliente", "BANCO": "Banco", "IMPLE": "Imple"}


def _ptype(qt: str) -> str:
    t = (qt or "").upper()
    return "LINK" if t in ("LINK_PAGO", "LINK") else "MPOS" if t == "FAST_TRACK" else t


def _stage(p: dict) -> str:
    return "por_asignar" if not p.get("assigned_to_name") else "asignado" if not p.get("ticket_number") else "en_gestion"


def _fmt(d: Optional[str]) -> str:
    return "—" if not d else "/".join(reversed(str(d)[:10].split("-")))


async def _rows(user: dict, implementador: str, generador: str, desde: str, hasta: str, tipo: str, estatus: str, nivel: str = ""):
    from routes.projects import _build_project_visibility_query
    from services.business_calendar import business_days_between, get_holiday_sets
    from services.project_sla_engine import DEFAULT_THRESHOLDS, sla_reference_date

    q = await _build_project_visibility_query(user)
    projects = await db.projects.find(q, {"_id": 0, "notification_history": 0, "status_history": 0}).to_list(5000)
    cfg = (await db.project_sla_config.find_one({"config_id": "default"}, {"_id": 0}) or {}).get("stages") or {}
    specific, recurring = await get_holiday_sets()
    today = datetime.now(timezone.utc).date()
    opts = {"implementadores": sorted({p["assigned_to_name"] for p in projects if p.get("assigned_to_name")}),
            "generadores": sorted({p["created_by_name"] for p in projects if p.get("created_by_name")}),
            "estatus": sorted({p["status"] for p in projects if p.get("status")})}
    rows = []
    for p in projects:
        sent = str(p.get("sent_to_implementation_at") or p.get("created_at") or "")[:10]
        if implementador and p.get("assigned_to_name") != implementador:
            continue
        if generador and p.get("created_by_name") != generador:
            continue
        if (desde and sent < desde) or (hasta and sent > hasta):
            continue
        if tipo and _ptype(p.get("quote_type")) != tipo:
            continue
        if estatus and p.get("status") != estatus:
            continue
        ref = sla_reference_date(p)
        days = business_days_between(ref.date(), today, specific, recurring) if ref else 0
        th = {**DEFAULT_THRESHOLDS.get(_stage(p), {}), **(cfg.get(_stage(p)) or {})}
        level = "al_dia" if p.get("status") in FINISHED else "critico" if days >= int(th.get("delay_days", 4)) \
            else "medio" if days >= int(th.get("warning_days", 2)) else "al_dia"
        seguim = max([b.get("created_at") or "" for b in (p.get("bitacora") or [])] + [str(p.get("last_qualified_activity_at") or "")])
        rows.append({"project_id": p["project_id"], "project_number": p.get("project_number", ""),
                     "cliente": p.get("client_name", ""), "tipo": TYPE_LABEL.get(_ptype(p.get("quote_type")), p.get("quote_type") or "—"),
                     "avance": round(float((p.get("rollup_progress") or {}).get("global_progress") or 0)),
                     "fecha_envio": sent, "fecha_asignacion": p.get("assigned_at") if p.get("assigned_to_name") else None,
                     "generador": p.get("created_by_name", ""), "implementador": p.get("assigned_to_name") or "Sin asignar",
                     "estado": p.get("status", ""), "responsable": MOTIVO_LABEL.get((p.get("motivo_avance") or "").upper(), "Sin responsable"),
                     "ultimo_seguimiento": seguim or None,
                     "dias_retraso": 0 if p.get("status") in FINISHED else days, "nivel": level, "nivel_label": LEVEL_LABEL[level]})
    if nivel:
        rows = [r for r in rows if r["nivel"] == nivel]
    order = {"critico": 0, "medio": 1, "al_dia": 2}
    rows.sort(key=lambda r: (order[r["nivel"]], -r["dias_retraso"], r["implementador"], r["project_number"]))
    kpis = {"total": len(rows), **{k: sum(r["nivel"] == k for r in rows) for k in order},
            "avance_promedio": round(sum(r["avance"] for r in rows) / len(rows)) if rows else 0}
    return rows, kpis, opts


HEAD = ["Proyecto", "Cliente", "Tipo", "% Avance", "Fecha Asignación", "Generador", "Implementador", "Estado",
        "Responsable del Avance", "Último Seguimiento", "Días Retraso", "Tipo de Retraso"]


def _vals(r):
    return [r["project_number"], r["cliente"], r["tipo"], f"{r['avance']}%", _fmt(r["fecha_asignacion"]), r["generador"],
            r["implementador"], r["estado"], r["responsable"], _fmt(r["ultimo_seguimiento"]), r["dias_retraso"], r["nivel_label"]]


def _xlsx(rows, kpis, ftext):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Seguimiento de Proyectos"
    ws.append(["Reporte de Seguimiento de Proyectos"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Filtros: {ftext}"])
    ws.append([f"Total: {kpis['total']}", f"Retraso Crítico: {kpis['critico']}", f"Retraso Medio: {kpis['medio']}",
               f"Al Día: {kpis['al_dia']}", f"Avance promedio: {kpis['avance_promedio']}%"])
    ws.append([])
    ws.append(HEAD)
    for c in ws[5]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E3A8A")
    fills = {"critico": "FEE2E2", "medio": "FEF3C7", "al_dia": "DCFCE7"}
    for r in rows:
        v = _vals(r)
        v[3] = r["avance"] / 100
        ws.append(v)
        ws.cell(row=ws.max_row, column=4).number_format = "0%"
        ws.cell(row=ws.max_row, column=12).fill = PatternFill("solid", fgColor=fills[r["nivel"]])
    for col, w in zip("ABCDEFGHIJKL", [24, 34, 16, 10, 15, 24, 24, 20, 20, 16, 12, 16]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A6"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _pdf(rows, kpis, ftext):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, legal
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from services.pdf_report import BRAND_BLUE, GRID_COLOR, _cell_style, _header_cell_style, _make_decorator

    title = "Reporte de Seguimiento de Proyectos"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(legal), leftMargin=0.4 * inch, rightMargin=0.4 * inch,
                            topMargin=1.15 * inch, bottomMargin=0.6 * inch, title=title)
    cs, hs = _cell_style(), _header_cell_style()
    cs = ParagraphStyle("c8", parent=cs, fontSize=7.5, leading=9.5)
    small = ParagraphStyle("small", parent=cs, fontSize=8, textColor=colors.HexColor("#475569"))
    P = lambda t, s=cs: Paragraph(escape(str(t if t is not None else "")), s)
    tone = {"critico": colors.HexColor("#FEE2E2"), "medio": colors.HexColor("#FEF3C7"), "al_dia": colors.HexColor("#DCFCE7")}

    kp = [("Total Proyectos", kpis["total"]), ("Retraso Crítico", kpis["critico"]), ("Retraso Medio", kpis["medio"]),
          ("Al Día", kpis["al_dia"]), ("Avance Promedio", f"{kpis['avance_promedio']}%")]
    kt = Table([[Paragraph(k, hs) for k, _ in kp], [P(v) for _, v in kp]], colWidths=[doc.width / 5] * 5)
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE), ("GRID", (0, 0), (-1, -1), 0.5, GRID_COLOR)]))
    widths = [.1, .14, .06, .05, .07, .1, .1, .08, .07, .07, .05, .07]
    data = [[Paragraph(h, hs) for h in HEAD]] + [[P(v) for v in _vals(r)] for r in rows]
    t = Table(data, colWidths=[doc.width * w for w in widths], repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE), ("GRID", (0, 0), (-1, -1), 0.5, GRID_COLOR), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    style += [("BACKGROUND", (11, i), (11, i), tone[r["nivel"]]) for i, r in enumerate(rows, start=1)]
    t.setStyle(TableStyle(style))
    story = [P(f"Filtros: {ftext}", small), Spacer(1, 6), kt, Spacer(1, 10), t if rows else P("No hay proyectos para los filtros seleccionados.")]
    deco = _make_decorator(title, BRAND_BLUE)
    doc.build(story, onFirstPage=deco, onLaterPages=deco)
    buf.seek(0)
    return buf


@router.get("/projects-report/followup")
async def followup_report(implementador: str = "", generador: str = "", desde: str = "", hasta: str = "", tipo: str = "",
                          estatus: str = "", nivel: str = "", authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    rows, kpis, opts = await _rows(user, implementador, generador, desde, hasta, tipo, estatus, nivel)
    return {"rows": rows, "kpis": kpis, "options": opts}


@router.get("/projects-report/followup/export")
async def followup_export(format: str = "pdf", implementador: str = "", generador: str = "", desde: str = "", hasta: str = "",
                          tipo: str = "", estatus: str = "", nivel: str = "", filters_label: str = "", authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if format not in ("pdf", "xlsx"):
        raise HTTPException(400, "Formato inválido")
    rows, kpis, _ = await _rows(user, implementador, generador, desde, hasta, tipo, estatus, nivel)
    ftext = filters_label or "Sin filtros (todos los proyectos visibles)"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if format == "xlsx":
        return StreamingResponse(_xlsx(rows, kpis, ftext), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": f'attachment; filename="Seguimiento_Proyectos_{stamp}.xlsx"'})
    return StreamingResponse(_pdf(rows, kpis, ftext), media_type="application/pdf",
                             headers={"Content-Disposition": f'inline; filename="Seguimiento_Proyectos_{stamp}.pdf"'})
