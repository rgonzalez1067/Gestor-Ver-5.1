"""Reporte Excel de Ediciones Maestras de Proyectos (una fila por campo cambiado)."""
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse

from config import db, get_current_user

from routes.auth import _effective_special_permissions
router = APIRouter()


def _fmt(v):
    return "—" if v in (None, "") else str(v)


@router.get("/project-master-edits/export-xlsx")
async def export_master_edits(date_from: str = "", date_to: str = "", authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if user.get("role") != "admin" and "proyectos:edicion_maestra" not in (await _effective_special_permissions(user)):
        raise HTTPException(status_code=403, detail="Requiere la Función Especial Edición Maestra.")
    rows = []
    cursor = db.projects.find({"bitacora.type": "master_override"},
                              {"_id": 0, "project_number": 1, "ticket_number": 1, "client_name": 1, "client_rif": 1, "bitacora": 1})
    async for p in cursor:
        for e in p.get("bitacora") or []:
            if e.get("type") != "master_override":
                continue
            day = (e.get("created_at") or "")[:10]
            if (date_from and day < date_from) or (date_to and day > date_to):
                continue
            base = [e.get("created_at") or "", p.get("project_number") or "", p.get("ticket_number") or "", p.get("client_name") or "",
                    p.get("client_rif") or "", e.get("created_by_name") or ""]
            just = e.get("justification") or "(sin justificación registrada)"
            changes = e.get("changes") or []
            if not changes:
                rows.append(base + ["(sin cambios efectivos)", "", "", just])
            for c in changes:
                rows.append(base + [c.get("label") or c.get("field") or "", _fmt(c.get("old")), _fmt(c.get("new")), just])
    rows.sort(key=lambda r: r[0], reverse=True)

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = "Ediciones Maestras"
    ws.append(["Fecha", "Proyecto", "Ticket", "Cliente", "RIF", "Usuario", "Campo", "Valor Anterior", "Valor Nuevo", "Justificación"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E293B")
    for r in rows:
        try:
            r[0] = datetime.fromisoformat(r[0].replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            pass
        ws.append(r)
        ws.cell(ws.max_row, 10).alignment = Alignment(wrap_text=True, vertical="top")
    for col, w in zip("ABCDEFGHIJ", (17, 16, 14, 34, 14, 22, 24, 30, 30, 60)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:J{max(ws.max_row, 1)}"
    buf = io.BytesIO()
    wb.save(buf)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return StreamingResponse(io.BytesIO(buf.getvalue()), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="Ediciones_Maestras_{stamp}.xlsx"'})
