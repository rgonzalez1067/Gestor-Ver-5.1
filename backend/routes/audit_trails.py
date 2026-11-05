"""Pistas de Auditoría: consulta global de solo lectura + exportación a Excel."""
import io
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from config import db, get_current_user
from services.audit_trail import AUDIT_COLLECTION, AUDIT_MODULES

router = APIRouter()
AUDITOR_PERMISSION = "configuracion:auditor"
EXPORT_LIMIT = 50000


def _coll():
    return db.raw[AUDIT_COLLECTION]


async def _require_auditor(authorization):
    user = await get_current_user(authorization)
    if user.get("role") == "admin" or AUDITOR_PERMISSION in (user.get("special_permissions") or []):
        return user
    raise HTTPException(status_code=403, detail="Solo Administradores o usuarios con permiso Auditor pueden consultar las Pistas de Auditoría")


def _parse_dt(v: Optional[str]):
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Fecha inválida: {v}")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _build_query(date_from, date_to, modules, action, user, registro, field):
    q = {}
    f, t = _parse_dt(date_from), _parse_dt(date_to)
    if f or t:
        q["fecha_hora"] = {**({"$gte": f} if f else {}), **({"$lte": t} if t else {})}
    mods = [m for m in (modules or "").split(",") if m.strip()]
    if mods:
        q["modulo"] = {"$in": mods}
    if action and action.upper() != "TODAS":
        q["accion"] = action.upper()
    if user:
        rx = {"$regex": re.escape(user.strip()), "$options": "i"}
        q["$or"] = [{"usuario_email": rx}, {"usuario_nombre": rx}]
    if registro:
        rx = {"$regex": re.escape(registro.strip()), "$options": "i"}
        q.setdefault("$and", []).append({"$or": [{"registro_id": rx}, {"entidad_id": rx}]})
    if field:
        q["campos_modificados"] = {"$regex": re.escape(field.strip()), "$options": "i"}
    return q


def _out(d):
    d["id"] = str(d.pop("_id"))
    if isinstance(d.get("fecha_hora"), datetime):
        fh = d["fecha_hora"]
        d["fecha_hora"] = (fh if fh.tzinfo else fh.replace(tzinfo=timezone.utc)).isoformat()
    return d


LIST_PROJECTION = {"valores_anteriores": 0, "valores_nuevos": 0}


@router.get("/audit-trails/filters")
async def audit_filters(authorization: Optional[str] = Header(None)):
    await _require_auditor(authorization)
    users = await db.raw.users.find({}, {"_id": 0, "email": 1, "first_name": 1, "last_name": 1}).sort("first_name", 1).to_list(2000)
    return {
        "modules": AUDIT_MODULES,
        "actions": ["CREATE", "UPDATE", "DELETE"],
        "users": [{"email": u.get("email", ""), "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()} for u in users],
    }


@router.get("/audit-trails")
async def list_audit_trails(
    authorization: Optional[str] = Header(None),
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    modules: Optional[str] = None, action: Optional[str] = None,
    user: Optional[str] = None, registro: Optional[str] = None, field: Optional[str] = None,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
):
    await _require_auditor(authorization)
    q = _build_query(date_from, date_to, modules, action, user, registro, field)
    total = await _coll().count_documents(q)
    total_all = await _coll().estimated_document_count()
    docs = await _coll().find(q, LIST_PROJECTION).sort("fecha_hora", -1).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    return {"items": [_out(d) for d in docs], "total": total, "total_all": total_all, "page": page, "page_size": page_size}


@router.get("/audit-trails/export")
async def export_audit_trails(
    authorization: Optional[str] = Header(None),
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    modules: Optional[str] = None, action: Optional[str] = None,
    user: Optional[str] = None, registro: Optional[str] = None, field: Optional[str] = None,
):
    await _require_auditor(authorization)
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    q = _build_query(date_from, date_to, modules, action, user, registro, field)
    wb = Workbook()
    ws = wb.active
    ws.title = "Pistas de Auditoría"
    headers = ["Fecha/Hora (UTC)", "Módulo", "Entidad", "Registro ID", "Acción", "Usuario", "Email", "IP Origen",
               "Endpoint", "Campos Modificados", "Valores Anteriores", "Valores Nuevos"]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="003366")
    import json
    import asyncio
    docs = [_out(d) for d in await _coll().find(q).sort("fecha_hora", -1).limit(EXPORT_LIMIT).to_list(EXPORT_LIMIT)]

    def _build():
        for d in docs:
            ws.append([
                d.get("fecha_hora", ""), d.get("modulo", ""), d.get("entidad", ""), d.get("registro_id", ""), d.get("accion", ""),
                d.get("usuario_nombre", ""), d.get("usuario_email", ""), d.get("ip_origen", ""), d.get("endpoint", ""),
                ", ".join(d.get("campos_modificados") or []),
                json.dumps(d.get("valores_anteriores"), ensure_ascii=False, default=str)[:32000] if d.get("valores_anteriores") is not None else "",
                json.dumps(d.get("valores_nuevos"), ensure_ascii=False, default=str)[:32000] if d.get("valores_nuevos") is not None else "",
            ])
        for col, w in zip("ABCDEFGHIJKL", (22, 20, 20, 26, 10, 24, 28, 16, 36, 40, 60, 60)):
            ws.column_dimensions[col].width = w
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return out

    buf = await asyncio.to_thread(_build)
    fname = f"pistas_auditoria_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/audit-trails/{trail_id}")
async def get_audit_trail(trail_id: str, authorization: Optional[str] = Header(None)):
    await _require_auditor(authorization)
    from bson import ObjectId
    from bson.errors import InvalidId
    try:
        oid = ObjectId(trail_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Pista no encontrada")
    d = await _coll().find_one({"_id": oid})
    if not d:
        raise HTTPException(status_code=404, detail="Pista no encontrada")
    return _out(d)
