"""Route module: economic_groups.py
Entidad "Grupo Económico": agrupa múltiples Clientes/RIFs bajo una figura
corporativa. Administra contactos corporativos (con perfilamiento) y
representantes legales. Sus contactos se heredan en cascada a los RIFs/Sucursales.
"""
import io
import re
import uuid
import logging
from services.report_header import draw_page_header
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header

from config import db, get_current_user, require_permission
from models import EconomicGroupCreate
from services.client_hierarchy import clean_characteristics, propagate_group

router = APIRouter()
logger = logging.getLogger(__name__)


def _name_regex(name: str) -> dict:
    return {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}


async def _rif_count(group_id: str) -> int:
    rifs = await db.clients.distinct("rif", {"grupo_economico_id": group_id})
    return len(rifs)


async def _associated_clients(group_id: str) -> list:
    """RIFs asociados al grupo. Una fila por RIF distinto (prefiere el Principal).
    Orden estricto de campos: Nombre de Fantasía, RIF, Nombre Jurídico."""
    docs = await db.clients.find(
        {"grupo_economico_id": group_id}, {"_id": 0}
    ).to_list(5000)
    by_rif: dict = {}
    for d in docs:
        rif = d.get("rif")
        if not rif:
            continue
        is_principal = not d.get("is_branch") and not d.get("parent_client_id")
        if rif not in by_rif or is_principal:
            by_rif[rif] = d
    rows = [{
        "client_id": d.get("client_id"),
        "fantasy_name": d.get("fantasy_name") or "",
        "rif": d.get("rif") or "",
        "legal_name": d.get("legal_name") or "",
    } for d in by_rif.values()]
    rows.sort(key=lambda r: (r["fantasy_name"] or "").lower())
    return rows


def _serialize(group: dict) -> dict:
    group.pop("_id", None)
    if isinstance(group.get("created_at"), datetime):
        group["created_at"] = group["created_at"].isoformat()
    return group


@router.get("/grupos-economicos")
async def list_economic_groups(search: str = "", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    query = {}
    if search.strip():
        query["name"] = {"$regex": re.escape(search.strip()), "$options": "i"}
    groups = await db.economic_groups.find(query, {"_id": 0}).sort("name", 1).to_list(2000)
    for g in groups:
        g["rif_count"] = await _rif_count(g["group_id"])
        g["contacts_count"] = len([c for c in (g.get("contacts") or []) if (c.get("email") or "").strip()])
        g["brands_count"] = await db.brands.count_documents({"group_id": g["group_id"]})
    return groups


@router.post("/grupos-economicos")
async def create_economic_group(payload: EconomicGroupCreate, authorization: Optional[str] = Header(None)):
    await require_permission(authorization, "grupos_economicos", "edit")
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre del grupo es obligatorio")
    existing = await db.economic_groups.find_one({"name": _name_regex(name)}, {"_id": 0, "group_id": 1})
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un Grupo Económico con el nombre '{name}'")
    data = payload.model_dump()
    data["name"] = name
    data["characteristics"] = clean_characteristics(payload.characteristics)
    for c in data.get("contacts", []):
        if not c.get("contact_id"):
            c["contact_id"] = f"cnt_{uuid.uuid4().hex[:8]}"
    group = {
        "group_id": f"grp_{uuid.uuid4().hex[:12]}",
        **data,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": None,
    }
    await db.economic_groups.insert_one(dict(group))
    return _serialize(group)


@router.get("/grupos-economicos/{group_id}")
async def get_economic_group(group_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    group = await db.economic_groups.find_one({"group_id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Grupo Económico no encontrado")
    clients = await _associated_clients(group_id)
    group["clients"] = clients
    group["rif_count"] = len(clients)
    group["brands_count"] = await db.brands.count_documents({"group_id": group_id})
    return _serialize(group)


@router.get("/grupos-economicos/{group_id}/clients")
async def get_economic_group_clients(group_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    group = await db.economic_groups.find_one({"group_id": group_id}, {"_id": 0, "group_id": 1})
    if not group:
        raise HTTPException(status_code=404, detail="Grupo Económico no encontrado")
    return await _associated_clients(group_id)


@router.put("/grupos-economicos/{group_id}")
async def update_economic_group(group_id: str, payload: EconomicGroupCreate, authorization: Optional[str] = Header(None)):
    await require_permission(authorization, "grupos_economicos", "edit")
    existing = await db.economic_groups.find_one({"group_id": group_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Grupo Económico no encontrado")
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre del grupo es obligatorio")
    dup = await db.economic_groups.find_one(
        {"name": _name_regex(name), "group_id": {"$ne": group_id}}, {"_id": 0, "group_id": 1}
    )
    if dup:
        raise HTTPException(status_code=400, detail=f"Ya existe otro Grupo Económico con el nombre '{name}'")
    data = payload.model_dump()
    data["name"] = name
    data["characteristics"] = clean_characteristics(payload.characteristics)
    for c in data.get("contacts", []):
        if not c.get("contact_id"):
            c["contact_id"] = f"cnt_{uuid.uuid4().hex[:8]}"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.economic_groups.update_one({"group_id": group_id}, {"$set": data})
    # Mantener sincronizado el nombre visible en los clientes vinculados
    await db.clients.update_many({"grupo_economico_id": group_id}, {"$set": {"grupo_economico": name}})
    await propagate_group(group_id)
    return await get_economic_group(group_id, authorization)


@router.delete("/grupos-economicos/{group_id}")
async def delete_economic_group(group_id: str, authorization: Optional[str] = Header(None)):
    await require_permission(authorization, "grupos_economicos", "edit")
    group = await db.economic_groups.find_one({"group_id": group_id}, {"_id": 0, "group_id": 1})
    if not group:
        raise HTTPException(status_code=404, detail="Grupo Económico no encontrado")
    # Desvincular clientes (no se borran) y limpiar el nombre de grupo heredado
    await db.clients.update_many(
        {"grupo_economico_id": group_id},
        {"$set": {"grupo_economico_id": None, "grupo_economico": None}},
    )
    await db.economic_groups.delete_one({"group_id": group_id})
    brand_ids = await db.brands.distinct("brand_id", {"group_id": group_id})
    await db.brands.update_many({"group_id": group_id}, {"$set": {"group_id": None}})
    from services.client_hierarchy import propagate_brand
    for bid in brand_ids:
        await propagate_brand(bid)
    return {"deleted": True, "group_id": group_id}


@router.get("/grupos-economicos/{group_id}/export-pdf")
async def export_economic_group_pdf(group_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    group = await db.economic_groups.find_one({"group_id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Grupo Económico no encontrado")
    from routes.brands_report import _report_data
    from services.rif_formatter import format_rif
    brand_ids = [b["brand_id"] for b in await db.brands.find({"group_id": group_id}, {"_id": 0, "brand_id": 1}).to_list(None)]
    brands = await _report_data(brand_ids) if brand_ids else []
    covered = {r["rif"] for b in brands for r in b["rifs"]}
    loose = [c for c in await _associated_clients(group_id) if format_rif(c["rif"]) not in covered]
    if loose:
        brands.append({"name": "Sin Marca asignada", "group": "", "rifs": [
            {"rif": format_rif(c["rif"]), "legal_name": c["legal_name"], "branches": 1, "segment": "", "ejecutivo": ""} for c in loose]})
    n_rifs = sum(len(b["rifs"]) for b in brands)
    n_br = sum(r["branches"] for b in brands for r in b["rifs"])
    n_brands = len(brand_ids)

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether,
    )

    ACCENT = "#4f46e5"
    ACCENT_DARK = "#3730a3"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=26 * mm, bottomMargin=16 * mm,
        title=f"Grupo Económico - {group.get('name', '')}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", parent=styles["Normal"], fontName="Helvetica-Bold",
                                 fontSize=15, textColor=colors.HexColor(ACCENT_DARK), leading=18)
    sub_style = ParagraphStyle("s", parent=styles["Normal"], fontName="Helvetica",
                               fontSize=10, textColor=colors.HexColor("#64748b"), leading=13)
    cell_style = ParagraphStyle("c", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=11)

    header_text = [
        Paragraph(f"Grupo Económico: {group.get('name', '')}", title_style),
        Paragraph(f"{n_brands} marcas · {n_rifs} RIF · {n_br} sucursales", sub_style),
    ]
    # El logo va solo en la banda superior (draw_page_header, esquina superior izquierda).
    header_row = Table([[header_text]], colWidths=[174 * mm])
    header_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    story = [header_row, Spacer(1, 6),
             HRFlowable(width="100%", thickness=1.2, color=colors.HexColor(ACCENT)), Spacer(1, 12)]

    brand_style = ParagraphStyle("b", parent=styles["Normal"], fontName="Helvetica-Bold",
                                 fontSize=10.5, textColor=colors.HexColor(ACCENT_DARK), leading=13)
    summary = Table([[f"{n_brands}", f"{n_rifs}", f"{n_br}"], ["Marcas", "RIF", "Sucursales"]], colWidths=[58 * mm] * 3)
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2ff")), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 16),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(ACCENT_DARK)), ("FONTSIZE", (0, 1), (-1, 1), 8.5),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#64748b")), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LINEAFTER", (0, 0), (1, -1), 0.6, colors.white),
    ]))
    story += [summary, Spacer(1, 14)]
    if not brands:
        story.append(Paragraph("Sin marcas ni RIF asociados.", cell_style))
    for b in brands:
        rows = [["RIF", "Razón Social", "Sucursales", "Segmento", "Ejecutivo Propietario"]]
        rows += [[r["rif"], Paragraph(r["legal_name"], cell_style), str(r["branches"]), r["segment"] or "—",
                  Paragraph(r["ejecutivo"] or "—", cell_style)] for r in b["rifs"]] or [["", Paragraph("Sin RIF asociados", cell_style), "", "", ""]]
        t = Table(rows, colWidths=[28 * mm, 62 * mm, 18 * mm, 26 * mm, 40 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(ACCENT)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        head = Paragraph(f"{b['name']}  <font size='8.5' color='#64748b'>· {len(b['rifs'])} RIF · {sum(r['branches'] for r in b['rifs'])} sucursales</font>", brand_style)
        block = [head, Spacer(1, 3), t]
        story += ([KeepTogether(block)] if len(rows) < 25 else block) + [Spacer(1, 10)]

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.drawString(18 * mm, 10 * mm, "Megasoft · Grupo Económico")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc_.page}")
        canvas.restoreState()
        draw_page_header(canvas, doc_, f"Grupo Económico - {group.get('name', '')}")

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    from fastapi.responses import StreamingResponse
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", group.get("name", "grupo"))
    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Grupo_{safe_name}.pdf"'},
    )
