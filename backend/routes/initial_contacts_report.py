"""Reporte: Análisis de la Gestión de Contactos Iniciales (filtros + interacciones). Solo Administrador."""
import io
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from config import db, get_current_user

router = APIRouter(tags=["initial-contacts-report"])
SEDE_LABEL = {"PYME": "Pyme", "CORP": "Corporativo"}
EVENT_LABEL = {"created": "Registro", "edited": "Edición", "assigned": "Asignación", "documented": "Documento",
               "transferred": "Transferencia", "converted": "Conversión a Cliente"}
STATUS_LABEL = {"converted": "Convertido a Cliente", "closed": "Cerrado", "active": "En Gestión"}


def _status(c: dict) -> str:
    if c.get("is_converted"):
        return "converted"
    return "closed" if c.get("status") == "closed" else "active"


def _fmt_dt(v: str) -> str:
    try:
        return datetime.fromisoformat((v or "").replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return v or ""


def _fmt_d(v: str) -> str:
    try:
        return datetime.fromisoformat((v or "")[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return v or ""


async def _build(referente_id: str, date_from: str, date_to: str, assigned_to: str, sede: str, status: str):
    q = {}
    if referente_id:
        q["referente_id"] = referente_id
    if assigned_to:
        q["assigned_to_user_id"] = assigned_to
    if sede:
        q["sede"] = sede
    if date_from or date_to:
        rng = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to + "T23:59:59.999999+99:99"
        q["created_at"] = rng
    contacts = await db.initial_contacts.find(q, {"_id": 0}).sort("created_at", -1).to_list(5000)
    if status:
        contacts = [c for c in contacts if _status(c) == status]
    ids = [c["contact_id"] for c in contacts]
    logs_by = {}
    async for lg in db.initial_contact_logs.find({"contact_id": {"$in": ids}}, {"_id": 0}):
        logs_by.setdefault(lg["contact_id"], []).append({
            "fecha": lg.get("created_at") or "", "tipo": lg.get("action") or "Seguimiento",
            "detalle": lg.get("detail") or "", "persona_contactada": lg.get("contacted_person") or "",
            "proximo_contacto": lg.get("follow_up_date") or "", "usuario": lg.get("created_by_name") or "",
            "completado": bool(lg.get("is_completed")),
        })
    items = []
    for c in contacts:
        inter = [{"fecha": b.get("timestamp") or "", "tipo": EVENT_LABEL.get(b.get("action"), (b.get("action") or "Evento").capitalize()),
                  "detalle": b.get("description") or "", "persona_contactada": "", "proximo_contacto": "",
                  "usuario": b.get("user_name") or "", "completado": True} for b in (c.get("bitacora") or [])]
        inter += logs_by.get(c["contact_id"], [])
        inter.sort(key=lambda i: i["fecha"], reverse=True)
        st = _status(c)
        items.append({
            "contact_id": c["contact_id"], "contact_name": c.get("contact_name") or "", "legal_name": c.get("legal_name") or "",
            "phone": c.get("phone") or "", "email": c.get("email") or "", "referido_por": c.get("referred_by") or "",
            "referente_id": c.get("referente_id"), "asignado": c.get("assigned_to_name") or "", "sede": c.get("sede") or "",
            "created_at": c.get("created_at") or "", "status": st, "status_label": STATUS_LABEL[st],
            "closed_reason": c.get("closed_reason") or "", "interest_notes": c.get("interest_notes") or "",
            "last_contact_date": c.get("last_contact_date") or "", "interacciones": inter,
        })
    total = len(items)
    conv = sum(1 for i in items if i["status"] == "converted")
    closed = sum(1 for i in items if i["status"] == "closed")
    n_inter = sum(len(i["interacciones"]) for i in items)
    kpis = {"total": total, "convertidos": conv, "cerrados": closed, "en_gestion": total - conv - closed,
            "tasa_conversion": round(conv * 100 / total, 1) if total else 0.0,
            "interacciones": n_inter, "promedio_interacciones": round(n_inter / total, 1) if total else 0.0}
    return items, kpis


async def _require_admin(authorization):
    user = await get_current_user(authorization)
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Solo el Administrador puede ver este reporte")
    return user


@router.get("/initial-contacts-report")
async def contacts_report(referente_id: str = "", date_from: str = "", date_to: str = "", assigned_to: str = "",
                          sede: str = "", status: str = "", authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    items, kpis = await _build(referente_id, date_from, date_to, assigned_to, sede, status)
    assignees = {}
    async for c in db.initial_contacts.find({"assigned_to_user_id": {"$nin": [None, ""]}}, {"_id": 0, "assigned_to_user_id": 1, "assigned_to_name": 1}):
        assignees[c["assigned_to_user_id"]] = c.get("assigned_to_name") or c["assigned_to_user_id"]
    return {"items": items, "kpis": kpis,
            "assignees": sorted(({"user_id": k, "name": v} for k, v in assignees.items()), key=lambda a: a["name"].casefold())}



def _xlsx(items, kpis, ftext):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Análisis de la Gestión de Contactos"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([f"Filtros: {ftext}"])
    ws.append([f"Generado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC"])
    ws.append([])
    for label, k in (("Total contactos", "total"), ("Convertidos a cliente", "convertidos"), ("Cerrados", "cerrados"),
                     ("En gestión", "en_gestion"), ("Tasa de conversión (%)", "tasa_conversion"),
                     ("Total interacciones", "interacciones"), ("Promedio interacciones por contacto", "promedio_interacciones")):
        ws.append([label, kpis[k]])
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 14

    def sheet(title, headers, rows, widths):
        s = wb.create_sheet(title)
        s.append(headers)
        for c in s[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="00447C")
        for r in rows:
            s.append(r)
            for cell in s[s.max_row]:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        for i, w in enumerate(widths):
            s.column_dimensions[chr(65 + i)].width = w
        s.freeze_panes = "A2"
        s.auto_filter.ref = f"A1:{chr(64 + len(headers))}{max(s.max_row, 1)}"

    sheet("Contactos", ["Fecha Registro", "Contacto", "Razón Social", "Teléfono", "Correo", "Referido Por", "Asignado a", "Segmento", "Estatus", "Interacciones", "Último Contacto", "Motivo Cierre", "Interés"],
          [[_fmt_d(i["created_at"]), i["contact_name"], i["legal_name"], i["phone"], i["email"], i["referido_por"], i["asignado"],
            SEDE_LABEL.get(i["sede"], i["sede"]), i["status_label"], len(i["interacciones"]), _fmt_d(i["last_contact_date"]),
            i["closed_reason"], i["interest_notes"]] for i in items],
          (13, 24, 28, 15, 26, 20, 22, 13, 18, 12, 14, 30, 40))
    sheet("Interacciones", ["Contacto", "Razón Social", "Referido Por", "Fecha", "Tipo", "Detalle", "Persona Contactada", "Próximo Contacto", "Usuario"],
          [[i["contact_name"], i["legal_name"], i["referido_por"], _fmt_dt(x["fecha"]), x["tipo"], x["detalle"], x["persona_contactada"],
            _fmt_d(x["proximo_contacto"]), x["usuario"]] for i in items for x in i["interacciones"]],
          (24, 28, 20, 17, 18, 60, 22, 15, 22))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _pdf(items, kpis, ftext):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from services.pdf_report import BRAND_BLUE, GRID_COLOR, _cell_style, _header_cell_style, _make_decorator

    title = "Análisis de la Gestión de Contactos"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                            topMargin=1.15 * inch, bottomMargin=0.6 * inch, title=title)
    cs, hs = _cell_style(), _header_cell_style()
    small = ParagraphStyle("small", parent=cs, fontSize=8, textColor=colors.HexColor("#475569"))
    h2 = ParagraphStyle("h2", parent=cs, fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=BRAND_BLUE)
    P = lambda t, s=cs: Paragraph(escape(str(t or "")), s)

    def grid(data, widths, color=BRAND_BLUE):
        t = Table(data, colWidths=[doc.width * w for w in widths], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), color), ("GRID", (0, 0), (-1, -1), 0.5, GRID_COLOR),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])]))
        return t

    story = [P(f"Filtros: {ftext}", small), Spacer(1, 6)]
    kp = [("Total", kpis["total"]), ("Convertidos", kpis["convertidos"]), ("Cerrados", kpis["cerrados"]), ("En gestión", kpis["en_gestion"]),
          ("Conversión", f"{kpis['tasa_conversion']}%"), ("Interacciones", kpis["interacciones"])]
    story += [grid([[Paragraph(k, hs) for k, _ in kp], [P(v) for _, v in kp]], [1 / 6] * 6), Spacer(1, 10)]
    story.append(grid([[Paragraph(h, hs) for h in ("Registro", "Contacto", "Razón Social", "Referido Por", "Asignado a", "Segmento", "Estatus", "Interac.")]] +
                      [[P(_fmt_d(i["created_at"])), P(i["contact_name"]), P(i["legal_name"]), P(i["referido_por"]), P(i["asignado"]),
                        P(SEDE_LABEL.get(i["sede"], i["sede"])), P(i["status_label"]), P(len(i["interacciones"]))] for i in items],
                      [.09, .17, .2, .14, .15, .09, .1, .06]))
    for i in items:
        story.append(Spacer(1, 12))
        head = P(f"{i['contact_name']} — {i['legal_name']}  ·  {i['status_label']}  ·  Referido por: {i['referido_por'] or '—'}  ·  Asignado: {i['asignado'] or '—'}", h2)
        if not i["interacciones"]:
            story.append(KeepTogether([head, P("Sin interacciones registradas.", small)]))
            continue
        rows = [[Paragraph(h, hs) for h in ("Fecha", "Tipo", "Detalle", "Persona Contactada", "Próximo", "Usuario")]] + \
               [[P(_fmt_dt(x["fecha"])), P(x["tipo"]), P(x["detalle"]), P(x["persona_contactada"]), P(_fmt_d(x["proximo_contacto"])), P(x["usuario"])]
                for x in i["interacciones"]]
        story += [head, Spacer(1, 3), grid(rows, [.11, .12, .43, .13, .08, .13], colors.HexColor("#334155"))]
    deco = _make_decorator(title, BRAND_BLUE)
    doc.build(story, onFirstPage=deco, onLaterPages=deco)
    buf.seek(0)
    return buf


@router.get("/initial-contacts-report/export")
async def export_contacts_report(format: str = "xlsx", referente_id: str = "", date_from: str = "", date_to: str = "",
                                 assigned_to: str = "", sede: str = "", status: str = "", filters_label: str = "",
                                 authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    if format not in ("xlsx", "pdf"):
        raise HTTPException(status_code=400, detail="Formato inválido")
    items, kpis = await _build(referente_id, date_from, date_to, assigned_to, sede, status)
    ftext = filters_label or "Sin filtros (todos los contactos)"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if format == "xlsx":
        return StreamingResponse(_xlsx(items, kpis, ftext), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": f'attachment; filename="Analisis_Contactos_{stamp}.xlsx"'})
    return StreamingResponse(_pdf(items, kpis, ftext), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="Analisis_Contactos_{stamp}.pdf"'})
