"""Reporte «Auditoría de Taller»: consistencia entre estatus de equipos y estatus de su cotización."""
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from config import db, get_current_user
from permissions_catalog import has_module_level

router = APIRouter(tags=["taller-audit"])

# Estatus del equipo → estatus esperado de la cotización (HISTORICO = cotización archivada).
EXPECTED = {"Cotizado": "Enviada", "En reparación": "Aprobada", "Reparado": "Facturada", "Pagado": "Pagada", "Entregado": "HISTORICO"}
ALIASES = {"Pagada": "Pagado", "Entregada": "Entregado", "En reparacion": "En reparación"}
LABEL = {"Pagado": "Pagada", "Entregado": "Entregada"}


def _diagnose(est: str, q: Optional[dict], ref: Optional[str] = None) -> tuple[str, str]:
    lbl = LABEL.get(est, est)
    if not q and ref:
        return "INCONSISTENCIA", f"INCONSISTENCIA: Equipo en estatus {lbl} tiene vinculada la cotización {ref}, pero no existe en Cotizaciones ni en el Histórico."
    if est == "Recibido":
        if q:
            return "ALERTA", f"ALERTA: Equipo recién recibido ya tiene cotización vinculada ({q['number']})."
        return "OK", "OK - Equipo recibido pendiente por cotizar"
    if est not in EXPECTED:
        return "ALERTA", f"ALERTA: Estatus de equipo «{est or '—'}» no reconocido por la matriz de auditoría."
    if not q:
        return "INCONSISTENCIA", f"INCONSISTENCIA: Equipo en estatus {lbl} no posee cotización registrada."
    exp = EXPECTED[est]
    if exp == "HISTORICO":
        if q["historico"]:
            return "OK", "OK - Estatus alineado con cotización (Histórico)"
        return "INCONSISTENCIA", "INCONSISTENCIA: Equipo en estatus Entregada pero su cotización aún no ha sido movida al Histórico."
    if q["status"] == exp and not q["historico"]:
        return "OK", "OK - Estatus alineado con cotización"
    actual = f"{q['status'] or 'sin estatus'}{' (Histórico)' if q['historico'] else ''}"
    return "INCONSISTENCIA", f"INCONSISTENCIA: Equipo en estatus {lbl} requiere cotización en {exp}, pero figura en {actual}."


async def _quotes_index(equipos: list) -> tuple[dict, dict]:
    ids = list({e["quote_id"] for e in equipos if e.get("quote_id")})
    nums = list({e["quote_number"] for e in equipos if e.get("quote_number")})
    by_id, by_num = {}, {}
    proj = {"_id": 0, "quote_id": 1, "quote_number": 1, "quote_status": 1, "archived": 1}
    async for h in db.quote_history.find({"$or": [{"quote_id": {"$in": ids}}, {"quote_number": {"$in": nums}}]},
                                         {"_id": 0, "quote_id": 1, "quote_number": 1, "quote_status_final": 1}):
        rec = {"number": h.get("quote_number"), "status": h.get("quote_status_final"), "historico": True}
        by_id[h.get("quote_id")] = rec
        by_num[h.get("quote_number")] = rec
    async for q in db.quotes.find({"$or": [{"quote_id": {"$in": ids}}, {"quote_number": {"$in": nums}}]}, proj):
        prev = by_id.get(q["quote_id"])
        rec = {"number": q.get("quote_number"), "status": q.get("quote_status"), "historico": bool(q.get("archived")) or bool(prev)}
        by_id[q["quote_id"]] = rec
        by_num[q.get("quote_number")] = rec
    return by_id, by_num


async def _build(resultado: str, estatus: Optional[str], q: Optional[str], desde: Optional[str], hasta: Optional[str], fecha_campo: str):
    flt = {}
    if estatus:
        flt["estatus"] = {"$in": [estatus] + [k for k, v in ALIASES.items() if v == estatus]}
    equipos = await db.taller_equipos.find(flt, {"_id": 0}).to_list(20000)
    by_id, by_num = await _quotes_index(equipos)
    cids = list({e.get("client_id") for e in equipos if e.get("client_id")})
    rifs = {c["client_id"]: c.get("rif", "") async for c in db.clients.find({"client_id": {"$in": cids}}, {"_id": 0, "client_id": 1, "rif": 1})}
    needle = (q or "").strip().lower()
    rows = []
    for e in equipos:
        fecha = (e.get("updated_at") if fecha_campo == "actualizacion" else e.get("fecha_ingreso")) or e.get("created_at") or ""
        if desde and fecha[:10] < desde:
            continue
        if hasta and fecha[:10] > hasta:
            continue
        rif = rifs.get(e.get("client_id"), "")
        if needle and needle not in f"{e.get('serial', '')} {e.get('client_name', '')} {rif}".lower():
            continue
        est = ALIASES.get(e.get("estatus"), e.get("estatus"))
        quote = by_id.get(e.get("quote_id")) or by_num.get(e.get("quote_number"))
        ref = e.get("quote_number") or e.get("quote_id")
        nivel, diag = _diagnose(est, quote, ref)
        rows.append({"taller_equipo_id": e.get("taller_equipo_id"), "serial": e.get("serial", ""), "modelo": e.get("modelo", ""),
                     "client_name": e.get("client_name", ""), "rif": rif, "estatus": LABEL.get(est, est),
                     "quote_number": quote["number"] if quote else None,
                     "quote_ref_missing": None if quote else ref,
                     "quote_status": (quote["status"] if quote else None),
                     "quote_historico": bool(quote and quote["historico"]),
                     "fecha_ingreso": e.get("fecha_ingreso"), "updated_at": e.get("updated_at"),
                     "nivel": nivel, "diagnostico": diag})
    kpis = {"total": len(rows), "consistentes": sum(r["nivel"] == "OK" for r in rows),
            "inconsistencias": sum(r["nivel"] == "INCONSISTENCIA" for r in rows), "alertas": sum(r["nivel"] == "ALERTA" for r in rows)}
    if resultado == "inconsistencias":
        rows = [r for r in rows if r["nivel"] != "OK"]
    elif resultado == "consistentes":
        rows = [r for r in rows if r["nivel"] == "OK"]
    rows.sort(key=lambda r: ({"INCONSISTENCIA": 0, "ALERTA": 1, "OK": 2}[r["nivel"]], r["client_name"], r["serial"]))
    return rows, kpis


async def _guard(authorization):
    user = await get_current_user(authorization)
    if not has_module_level(user, "taller_auditoria", "read"):
        raise HTTPException(403, "No tiene acceso al reporte Auditoría de Taller")


@router.get("/reports/taller-audit")
async def taller_audit(resultado: str = "inconsistencias", estatus: Optional[str] = None, q: Optional[str] = None,
                       desde: Optional[str] = None, hasta: Optional[str] = None, fecha_campo: str = "ingreso",
                       authorization: Optional[str] = Header(None)):
    await _guard(authorization)
    rows, kpis = await _build(resultado, estatus, q, desde, hasta, fecha_campo)
    return {"kpis": kpis, "rows": rows}


@router.get("/reports/taller-audit/export")
async def taller_audit_export(resultado: str = "inconsistencias", estatus: Optional[str] = None, q: Optional[str] = None,
                              desde: Optional[str] = None, hasta: Optional[str] = None, fecha_campo: str = "ingreso",
                              authorization: Optional[str] = Header(None)):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    await _guard(authorization)
    rows, kpis = await _build(resultado, estatus, q, desde, hasta, fecha_campo)
    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoría de Taller"
    ws.append(["Reporte de Auditoría de Taller (Consistencia Equipo vs. Cotización)"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Total auditados: {kpis['total']}", f"Consistentes: {kpis['consistentes']}", f"Inconsistencias: {kpis['inconsistencias']}", f"Alertas: {kpis['alertas']}"])
    ws.append([])
    head = ["Serial", "Modelo", "Cliente", "RIF", "Estatus Equipo", "Cotización", "Estatus Cotización", "Fecha Ingreso", "Resultado", "Diagnóstico de Auditoría"]
    ws.append(head)
    for c in ws[4]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E293B")
    fills = {"INCONSISTENCIA": "FEE2E2", "ALERTA": "FEF3C7", "OK": "DCFCE7"}
    for r in rows:
        ws.append([r["serial"], r["modelo"], r["client_name"], r["rif"], r["estatus"], r["quote_number"] or (f"{r['quote_ref_missing']} (NO EXISTE)" if r["quote_ref_missing"] else "SIN COTIZACIÓN"),
                   (r["quote_status"] or "—") + (" (Histórico)" if r["quote_historico"] else ""),
                   (r["fecha_ingreso"] or "")[:10], {"OK": "Consistente"}.get(r["nivel"], r["nivel"].capitalize()), r["diagnostico"]])
        ws.cell(row=ws.max_row, column=9).fill = PatternFill("solid", fgColor=fills[r["nivel"]])
    for col, w in zip("ABCDEFGHIJ", [18, 26, 38, 15, 15, 24, 22, 13, 15, 90]):
        ws.column_dimensions[col].width = w
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    name = f"Auditoria_Taller_{datetime.now(timezone.utc).strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
