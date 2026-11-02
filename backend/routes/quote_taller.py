"""Endpoints del módulo "Taller" y catálogo de insumos para reparaciones.

Extraído de `quote_actions.py` para separar la gestión de equipos físicos en taller
y exports relacionados.
"""
from fastapi import APIRouter, HTTPException, Header, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import io
import uuid
import base64
import logging

from config import db, get_current_user
from services.other_actions_engine import dispatch_other_action


router = APIRouter()
logger = logging.getLogger(__name__)

# Estatus desde los cuales un serial puede liberarse a 'Recibido' al modificar la cotización.
_RELEASABLE = ["Recibido", "Cotizado", "En reparación"]


def _quote_link_filter(quote_id: str, quote_number: str) -> dict:
    ors = [{"quote_id": quote_id}]
    if quote_number:
        ors.append({"quote_number": quote_number})
    return {"$or": ors}


async def transfer_repair_serials(orig: dict, new_quote_id: str, new_quote_number: str) -> List[str]:
    """Nueva versión: libera los seriales de la cotización original (vuelven a 'Recibido')
    y los precarga en la nueva versión (quedan 'Cotizado' vinculados a ella)."""
    now = datetime.now(timezone.utc).isoformat()
    flt = {**_quote_link_filter(orig["quote_id"], orig.get("quote_number", "")),
           "estatus": {"$in": _RELEASABLE}}
    docs = await db.taller_equipos.find(flt, {"_id": 0, "taller_equipo_id": 1}).to_list(5000)
    ids = [d["taller_equipo_id"] for d in docs]
    if ids:
        await db.taller_equipos.update_many(
            {"taller_equipo_id": {"$in": ids}},
            {"$set": {"estatus": "Cotizado", "quote_id": new_quote_id,
                      "quote_number": new_quote_number, "updated_at": now}},
        )
    await db.quotes.update_one(
        {"quote_id": orig["quote_id"]},
        {"$set": {"linked_taller_equipo_ids": [], "released_taller_equipo_ids": ids,
                  "serials_released_to": new_quote_number, "updated_at": now}},
    )
    logger.info(f"[repair-serials] {len(ids)} serial(es) liberados de {orig.get('quote_number')} → {new_quote_number}")
    return ids


PAGO_VALIDADO_ACTIONS = ("pago_validado", "pago_validado_rep", "pago_validado_eq", "valid_pago", "validar_pago")


def is_pago_validado_action(action_id: str, label: str = "") -> bool:
    return action_id in PAGO_VALIDADO_ACTIONS or (label or "").strip().lower() == "validar pago"


async def mark_repair_serials_paid(quote: dict) -> int:
    """'Validar Pago' en reparación: equipos de la cotización pasan a 'Pagado'.
    'En reparación' (legacy) solo si la cotización ya fue marcada como Reparada."""
    src = ["Reparado"]
    if quote.get("repaired_at") or quote.get("quote_status") in ("Reparada", "Pagada"):
        src.append("En reparación")
    res = await db.taller_equipos.update_many(
        {**_quote_link_filter(quote["quote_id"], quote.get("quote_number", "")), "estatus": {"$in": src}},
        {"$set": {"estatus": "Pagado", "paid_at": datetime.now(timezone.utc).isoformat(),
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.modified_count:
        logger.info(f"[repair-paid] {res.modified_count} equipo(s) de {quote.get('quote_number')} → 'Pagado'")
    return res.modified_count


async def backfill_repair_paid_serials() -> int:
    """Sincroniza cotizaciones de reparación con pago ya validado (idempotente)."""
    ors = [{f"custom_actions_executed.{a}": {"$exists": True, "$ne": None}} for a in PAGO_VALIDADO_ACTIONS]
    total = 0
    async for q in db.quotes.find({"quote_category": "repair", "$or": ors},
                                  {"_id": 0, "quote_id": 1, "quote_number": 1, "repaired_at": 1, "quote_status": 1}):
        total += await mark_repair_serials_paid(q)
    return total


async def release_quote_serials(quote: dict) -> int:
    """Al eliminar una cotización de reparación: sus seriales vuelven a 'Recibido'."""
    now = datetime.now(timezone.utc).isoformat()
    res = await db.taller_equipos.update_many(
        {**_quote_link_filter(quote["quote_id"], quote.get("quote_number", "")),
         "estatus": {"$in": _RELEASABLE}},
        {"$set": {"estatus": "Recibido", "quote_id": None, "quote_number": None, "updated_at": now}},
    )
    logger.info(f"[repair-serials] {res.modified_count} serial(es) liberados al eliminar {quote.get('quote_number')}")
    return res.modified_count


async def sync_repair_serials(quote: dict, items: List[dict]) -> dict:
    """Sincroniza taller_equipos con los seriales de los ítems (N:N, un serial puede estar
    en varias líneas). Libera a 'Recibido' los que ya no están en ninguna línea y vincula
    ('Cotizado') los nuevos tomados del pool 'Recibido' del cliente."""
    now = datetime.now(timezone.utc).isoformat()
    qid, qnum, cid = quote["quote_id"], quote.get("quote_number", ""), quote.get("client_id", "")
    wanted: List[str] = []
    for it in items or []:
        if it.get("no_serial"):
            continue
        for s in it.get("serials") or []:
            s = str(s).strip()
            if s and s not in wanted:
                wanted.append(s)

    linked = await db.taller_equipos.find(
        {**_quote_link_filter(qid, qnum), "estatus": {"$in": _RELEASABLE}}, {"_id": 0},
    ).to_list(5000)
    to_release = [d["taller_equipo_id"] for d in linked if d.get("serial") not in wanted]
    if to_release:
        await db.taller_equipos.update_many(
            {"taller_equipo_id": {"$in": to_release}},
            {"$set": {"estatus": "Recibido", "quote_id": None, "quote_number": None, "updated_at": now}},
        )
    kept = [d for d in linked if d.get("serial") in wanted]
    kept_serials = {d.get("serial") for d in kept}
    missing = [s for s in wanted if s not in kept_serials]
    new_docs = []
    if missing and cid:
        cand = await db.taller_equipos.find(
            {"client_id": cid, "serial": {"$in": missing}, "estatus": "Recibido"}, {"_id": 0},
        ).to_list(5000)
        seen = set()
        for d in cand:
            if d.get("serial") not in seen:
                seen.add(d.get("serial")); new_docs.append(d)
        if new_docs:
            await db.taller_equipos.update_many(
                {"taller_equipo_id": {"$in": [d["taller_equipo_id"] for d in new_docs]}},
                {"$set": {"estatus": "Cotizado", "quote_id": qid, "quote_number": qnum, "updated_at": now}},
            )
    # Auto-sanear quote_id de los conservados (desalineación tras restores).
    stale = [d["taller_equipo_id"] for d in kept if d.get("quote_id") != qid]
    if stale:
        await db.taller_equipos.update_many(
            {"taller_equipo_id": {"$in": stale}}, {"$set": {"quote_id": qid, "updated_at": now}},
        )

    final_docs = kept + new_docs
    result = {"released": len(to_release), "linked_new": len(new_docs)}
    had_links = bool(linked) or bool(quote.get("linked_taller_equipo_ids"))
    if not final_docs and not had_links:
        return result  # Cotización legacy (seriales manuales sin registros de taller)

    # Reconstruir el pool (repair_models) desde taller + seriales legacy aún usados.
    legacy_model = {}
    for m in quote.get("repair_models") or []:
        for s in m.get("serials") or []:
            legacy_model[s] = (m.get("model_name", ""), m.get("model_id", ""))
    groups = {}
    for d in final_docs:
        key = (d.get("modelo") or "Equipo", d.get("modelo_id") or "")
        groups.setdefault(key, []).append(d.get("serial"))
    taller_serials = {d.get("serial") for d in final_docs}
    for s in wanted:
        if s not in taller_serials and s in legacy_model:
            groups.setdefault(legacy_model[s], []).append(s)
    repair_models = [{"model_name": k[0], "model_id": k[1], "quantity": len(v), "serials": v}
                     for k, v in groups.items()]
    await db.quotes.update_one(
        {"quote_id": qid},
        {"$set": {"linked_taller_equipo_ids": [d["taller_equipo_id"] for d in final_docs],
                  "repair_models": repair_models}},
    )
    logger.info(f"[repair-serials] {qnum}: liberados={len(to_release)} nuevos={len(new_docs)} total={len(final_docs)}")
    return result


class RecepcionModelo(BaseModel):
    model_id: str = ""
    model_name: str
    serials: List[str] = []


class RecepcionRequest(BaseModel):
    client_id: str
    client_name: str = ""
    client_rif: str = ""
    detalles_recepcion: str = ""
    models: List[RecepcionModelo] = []


@router.post("/taller/recepcion")
async def recepcion_equipos(payload: RecepcionRequest, authorization: Optional[str] = Header(None)):
    """Registra la recepción física de equipos en el Taller con estatus 'Recibido'
    y dispara la notificación configurable 'taller_recepcion_equipos'.
    """
    user = await get_current_user(authorization)
    client = await db.clients.find_one({"client_id": payload.client_id}, {"_id": 0}) or {}
    client_name = (payload.client_name or client.get("fantasy_name")
                   or client.get("legal_name") or client.get("commercial_name") or "").strip()
    client_rif = (payload.client_rif or client.get("rif") or "").strip()
    client_email = (client.get("email") or "").strip()
    if not client_email:
        for c in (client.get("contacts") or []):
            if (c.get("email") or "").strip():
                client_email = c["email"].strip()
                break

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    created_ids = []
    equipos_desc = []
    equipos_pairs = []
    for m in payload.models:
        serials = [s.strip() for s in (m.serials or []) if s and s.strip()]
        for s in serials:
            doc = {
                "taller_equipo_id": f"te_{uuid.uuid4().hex[:12]}",
                "serial": s,
                "modelo": m.model_name,
                "modelo_id": m.model_id,
                "client_id": payload.client_id,
                "client_name": client_name,
                "quote_id": None,
                "quote_number": None,
                "estatus": "Recibido",
                "fecha_ingreso": now_iso,
                "fecha_entrega": None,
                "fecha_recepcion": now_iso,
                "recibido_por": user.get("email"),
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            await db.taller_equipos.insert_one(doc)
            created_ids.append(doc["taller_equipo_id"])
            equipos_desc.append(f"{m.model_name} · Serial {s}")
            equipos_pairs.append((m.model_name, s))

    if not created_ids:
        raise HTTPException(status_code=400, detail="Debe incluir al menos un equipo con serial")

    from zoneinfo import ZoneInfo
    fecha_str = now.astimezone(ZoneInfo("America/Caracas")).strftime("%d/%m/%Y %H:%M")
    detalles = (payload.detalles_recepcion or "").strip()[:500]
    tpl_vars = {
        "Nombre_Cliente": client_name, "nombre_cliente": client_name,
        "Rif_Cliente": client_rif, "rif_cliente": client_rif,
        "Cantidad_Equipos": str(len(created_ids)),
        "Equipos_Recibidos": "\n".join(f"- {e}" for e in equipos_desc),
        "Equipos_Recibidos_HTML": "<br>".join(equipos_desc),
        "Fecha_Recepcion": fecha_str, "fecha_sistema": fecha_str,
        "usuario_ejecutor": user.get("email", ""),
        # Instrucciones especiales que el receptor deja al Equipo de Operaciones.
        "Detalles_Recepcion_Equipos": detalles,
        "detalles_recepcion_equipos": detalles,
    }
    try:
        pdf_bytes = _generate_reception_pdf(client_name, client_rif, equipos_pairs, fecha_str, user.get("email", ""))
        pdf_att = [{
            "filename": f"Comprobante_Recepcion_{(client_name or 'Cliente').replace(' ', '_')[:40]}.pdf",
            "content": base64.b64encode(pdf_bytes).decode("utf-8"),
        }]
    except Exception as e:  # noqa: BLE001
        logger.error(f"[taller-recepcion] fallo al generar PDF comprobante: {e}")
        pdf_att = None

    try:
        await dispatch_other_action(
            "taller_recepcion_equipos", tpl_vars, current_user=user,
            fallback_subject=f"Recepción de equipos en taller — {client_name}",
            extra_cc=[client_email] if client_email else None,
            extra_attachments=pdf_att,
            client=client,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[taller-recepcion] fallo al notificar: {e}")

    return {"success": True, "created": len(created_ids), "estatus": "Recibido"}


def _generate_reception_pdf(client_name, client_rif, equipos, fecha_str, user_email):
    """Genera el PDF 'Comprobante de Recepción de Equipos' (bytes)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas as rl_canvas

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    from config import UPLOADS_DIR
    logo_file = next(iter(sorted(UPLOADS_DIR.glob("logo.*"))), None)

    def header(y0):
        if logo_file:
            try:
                c.drawImage(str(logo_file), w - 2.5 * cm - 4.5 * cm, y0 - 0.7 * cm,
                            width=4.5 * cm, height=1.6 * cm, preserveAspectRatio=True,
                            anchor="e", mask="auto")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[taller-recepcion] logo no disponible: {e}")
        c.setFillColorRGB(0.08, 0.16, 0.28)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2.5 * cm, y0, "Comprobante de Recepción de Equipos")
        c.setFont("Helvetica", 9); c.setFillGray(0.45)
        c.drawString(2.5 * cm, y0 - 0.55 * cm, "Gestión de Taller · Mega Soft")
        c.setFillGray(0)
        return y0 - 1.4 * cm

    y = header(h - 2.6 * cm)
    c.setFont("Helvetica", 11)
    for line in [f"Cliente: {client_name}", f"RIF: {client_rif}",
                 f"Fecha de recepción: {fecha_str}", f"Recibido por: {user_email}"]:
        c.drawString(2.5 * cm, y, line); y -= 0.55 * cm

    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5 * cm, y, f"Equipos recibidos ({len(equipos)})")
    y -= 0.7 * cm

    from reportlab.lib.utils import simpleSplit

    # Agrupar por modelo preservando el orden de aparición: una cabecera por modelo
    # y debajo sus seriales (evita repetir la descripción larga y su solape).
    groups = []
    idx = {}
    for modelo, serial in equipos:
        key = str(modelo)
        if key not in idx:
            idx[key] = len(groups)
            groups.append((key, []))
        groups[idx[key]][1].append(str(serial))

    left = 2.5 * cm
    max_w = w - 2.5 * cm - 2.5 * cm  # ancho útil para el nombre del modelo
    running = 0
    for modelo, serials in groups:
        # Salto de página si no cabe al menos la cabecera + un serial
        if y < 3.6 * cm:
            c.showPage(); y = header(h - 2.6 * cm)
        # Cabecera del modelo (envuelve si es muy larga)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(0.08, 0.16, 0.28)
        for ml in simpleSplit(modelo, "Helvetica-Bold", 10, max_w):
            if y < 2.6 * cm:
                c.showPage(); y = header(h - 2.6 * cm)
                c.setFont("Helvetica-Bold", 10); c.setFillColorRGB(0.08, 0.16, 0.28)
            c.drawString(left, y, ml); y -= 0.5 * cm
        c.setStrokeGray(0.82)
        c.line(left, y + 0.28 * cm, w - 2.5 * cm, y + 0.28 * cm)
        # Seriales del modelo, uno por línea con numeración global
        c.setFillGray(0); c.setFont("Helvetica", 9)
        for s in serials:
            running += 1
            if y < 2.6 * cm:
                c.showPage(); y = header(h - 2.6 * cm); c.setFont("Helvetica", 9)
            c.drawString(left + 0.7 * cm, y, f"{running}.")
            c.drawString(left + 1.8 * cm, y, s[:60])
            y -= 0.45 * cm
        y -= 0.35 * cm  # separación entre modelos

    c.setFont("Helvetica", 8); c.setFillGray(0.5)
    c.drawString(2.5 * cm, 1.8 * cm,
                 "Documento generado automáticamente. Estatus asignado a los equipos: \"Recibido\".")
    c.showPage(); c.save(); buf.seek(0)
    return buf.getvalue()


@router.get("/taller/pending-count")
async def get_taller_pending_count(authorization: Optional[str] = Header(None)):
    """Contador de equipos en taller con estatus 'Recibido' (pendientes por cotizar).
    Usado por el badge del menú de Gestión de Taller."""
    await get_current_user(authorization)
    count = await db.taller_equipos.count_documents({"estatus": "Recibido"})
    return {"pending": count}


@router.get("/taller/equipos-disponibles")
async def get_equipos_disponibles(client_id: str, authorization: Optional[str] = Header(None)):
    """Lista los equipos con estatus 'Recibido' de un cliente para vincularlos a una
    cotización de reparación (Fase 2 - Trazabilidad de Taller)."""
    await get_current_user(authorization)
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id es requerido")
    equipos = await db.taller_equipos.find(
        {"client_id": client_id, "estatus": "Recibido"},
        {"_id": 0, "taller_equipo_id": 1, "serial": 1, "modelo": 1, "modelo_id": 1,
         "fecha_ingreso": 1, "fecha_recepcion": 1},
    ).sort("fecha_ingreso", 1).to_list(1000)
    return {"equipos": equipos, "total": len(equipos)}


@router.post("/taller/parse-serials")
async def parse_serials_excel(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    """Extrae la lista de seriales (única, en orden) de un Excel para la Recepción."""
    await get_current_user(authorization)
    import openpyxl
    if not (file.filename or "").endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato Excel (.xlsx)")
    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), read_only=True)
        ws = wb.active
        seen, serials = set(), []
        skip = ('serial', 'seriales', 'numero de serie', 'número de serie', 'serial number', 'nro', 'n/s')
        for row in ws.iter_rows(min_row=1, values_only=True):
            for cell in row:
                if cell is None:
                    continue
                val = str(cell).strip()
                if val and val.lower() not in skip and val not in seen:
                    seen.add(val); serials.append(val)
        wb.close()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Error al leer el Excel: {str(e)}")
    if not serials:
        raise HTTPException(status_code=400, detail="No se encontraron seriales en el archivo")
    return {"serials": serials, "count": len(serials)}


@router.get("/repair-supplies")
async def get_repair_supplies(authorization: Optional[str] = Header(None)):
    """Lista bienes tipo Accesorio y Componente para carga de insumos en reparaciones."""
    await get_current_user(authorization)
    items = await db.hardware.find(
        {"type": {"$in": ["Accesorio", "Componente", "Pieza"]}},
        {"_id": 0, "hardware_id": 1, "name": 1, "type": 1, "category": 1, "price_usd": 1}
    ).sort("name", 1).to_list(500)
    return items


@router.get("/taller-equipos")
async def get_taller_equipos(
    authorization: Optional[str] = Header(None),
    client_id: Optional[str] = None,
    estatus: Optional[str] = None,
    search: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    """Consultar equipos en taller con filtros y cálculo de días en servidor."""
    await get_current_user(authorization)
    query = {}
    if client_id:
        query["client_id"] = client_id
    if estatus:
        query["estatus"] = estatus
    if search:
        search_re = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"serial": search_re},
            {"client_name": search_re},
            {"modelo": search_re},
            {"quote_number": search_re},
        ]
    if fecha_desde or fecha_hasta:
        date_filter = {}
        if fecha_desde:
            date_filter["$gte"] = fecha_desde
        if fecha_hasta:
            date_filter["$lte"] = fecha_hasta + "T23:59:59"
        query["fecha_ingreso"] = date_filter

    equipos = await db.taller_equipos.find(query, {"_id": 0}).to_list(2000)

    # Enriquecer con client_legal_name (Razón Social) para tooltip en grilla
    client_ids = list({e.get("client_id") for e in equipos if e.get("client_id")})
    legal_map = {}
    if client_ids:
        async for c in db.clients.find(
            {"client_id": {"$in": client_ids}},
            {"_id": 0, "client_id": 1, "legal_name": 1, "fantasy_name": 1},
        ):
            legal_map[c["client_id"]] = {
                "legal_name": c.get("legal_name", ""),
                "fantasy_name": c.get("fantasy_name", ""),
            }
    for eq in equipos:
        info = legal_map.get(eq.get("client_id"), {})
        eq["client_legal_name"] = info.get("legal_name", "")
        eq["client_fantasy_name"] = info.get("fantasy_name", "")

    # Calcular dias_en_taller en el servidor
    now = datetime.now(timezone.utc)
    for eq in equipos:
        fecha_ingreso_str = eq.get("fecha_ingreso", "")
        if fecha_ingreso_str:
            try:
                fi = datetime.fromisoformat(fecha_ingreso_str.replace("Z", "+00:00"))
                if fi.tzinfo is None:
                    fi = fi.replace(tzinfo=timezone.utc)
                delta = now - fi
                eq["dias_en_taller"] = max(delta.days, 0)
            except Exception:
                eq["dias_en_taller"] = 0
        else:
            eq["dias_en_taller"] = 0
        eq["alerta_retraso"] = eq["estatus"] == "En reparación" and eq["dias_en_taller"] > 15

    # Estadísticas
    total_en_reparacion = sum(1 for e in equipos if e.get("estatus") == "En reparación")
    total_entregados = sum(1 for e in equipos if e.get("estatus") == "Entregado")
    total_alerta = sum(1 for e in equipos if e.get("alerta_retraso"))

    return {
        "equipos": equipos,
        "total": len(equipos),
        "total_en_reparacion": total_en_reparacion,
        "total_entregados": total_entregados,
        "total_alerta": total_alerta,
    }


@router.get("/taller-equipos/{taller_equipo_id}/historial")
async def get_taller_equipo_historial(taller_equipo_id: str, authorization: Optional[str] = Header(None)):
    """Obtener historial/detalle de un equipo en taller."""
    await get_current_user(authorization)

    equipo = await db.taller_equipos.find_one({"taller_equipo_id": taller_equipo_id}, {"_id": 0})
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado en taller")

    # Calcular dias_en_taller
    now = datetime.now(timezone.utc)
    fecha_ingreso_str = equipo.get("fecha_ingreso", "")
    if fecha_ingreso_str:
        try:
            fi = datetime.fromisoformat(fecha_ingreso_str.replace("Z", "+00:00"))
            if fi.tzinfo is None:
                fi = fi.replace(tzinfo=timezone.utc)
            equipo["dias_en_taller"] = max((now - fi).days, 0)
        except Exception:
            equipo["dias_en_taller"] = 0

    # Obtener datos de la cotización
    quote = await db.quotes.find_one(
        {"quote_id": equipo.get("quote_id")},
        {"_id": 0, "status_history": 1, "quote_number": 1, "quote_status": 1, "created_by_user_id": 1, "approved_at": 1}
    )

    # Obtener usuario que creó/aprobó
    user_info = None
    if quote and quote.get("created_by_user_id"):
        user_info = await db.users.find_one(
            {"user_id": quote["created_by_user_id"]},
            {"_id": 0, "first_name": 1, "last_name": 1, "email": 1},
        )

    return {
        "equipo": equipo,
        "cotizacion": {
            "quote_number": quote.get("quote_number", "") if quote else "",
            "quote_status": quote.get("quote_status", "") if quote else "",
            "approved_at": quote.get("approved_at", "") if quote else "",
            "status_history": quote.get("status_history", []) if quote else [],
        },
        "recibido_por": {
            "nombre": f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() if user_info else "Sistema",
            "email": user_info.get("email", "") if user_info else "",
        },
    }


@router.get("/taller-equipos/export-excel")
async def export_taller_equipos_excel(
    authorization: Optional[str] = Header(None),
    estatus: Optional[str] = None,
    search: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    """Exportar equipos en taller a Excel."""
    await get_current_user(authorization)

    query = {}
    if estatus:
        query["estatus"] = estatus
    if search:
        search_re = {"$regex": search, "$options": "i"}
        query["$or"] = [{"serial": search_re}, {"client_name": search_re}, {"modelo": search_re}, {"quote_number": search_re}]
    if fecha_desde or fecha_hasta:
        date_filter = {}
        if fecha_desde:
            date_filter["$gte"] = fecha_desde
        if fecha_hasta:
            date_filter["$lte"] = fecha_hasta + "T23:59:59"
        query["fecha_ingreso"] = date_filter

    equipos = await db.taller_equipos.find(query, {"_id": 0}).to_list(2000)

    now = datetime.now(timezone.utc)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Equipos en Taller"

    # Header styles
    header_font = Font(bold=True, color="FFFFFF", size=10)
    header_fill = PatternFill(start_color="00447C", end_color="00447C", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )
    red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    red_font = Font(color="991B1B", bold=True)

    headers = ["Serial", "Modelo", "Cliente", "Cotizacion Origen", "Estatus", "Fecha Ingreso", "Fecha Entrega", "Dias en Taller"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    for row_idx, eq in enumerate(equipos, 2):
        fecha_ingreso_str = eq.get("fecha_ingreso", "")
        dias = 0
        if fecha_ingreso_str:
            try:
                fi = datetime.fromisoformat(fecha_ingreso_str.replace("Z", "+00:00"))
                if fi.tzinfo is None:
                    fi = fi.replace(tzinfo=timezone.utc)
                dias = max((now - fi).days, 0)
            except Exception:
                pass

        fecha_entrega_str = eq.get("fecha_entrega") or ""
        is_alert = eq.get("estatus") == "En reparación" and dias > 15

        values = [
            eq.get("serial", ""),
            eq.get("modelo", ""),
            eq.get("client_name", ""),
            eq.get("quote_number", ""),
            eq.get("estatus", ""),
            fecha_ingreso_str[:10] if fecha_ingreso_str else "",
            fecha_entrega_str[:10] if fecha_entrega_str else "",
            dias,
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = thin_border
            if is_alert:
                cell.fill = red_fill
                if col == 8:
                    cell.font = red_font

    # Adjust column widths
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"equipos_taller_{now.strftime('%Y%m%d')}.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


class EstatusUpdateRequest(BaseModel):
    estatus: str
    motivo: str = ""


VALID_TALLER_ESTATUS = ["Recibido", "Cotizado", "En reparación", "Reparado", "Pagado", "Entregado"]


@router.put("/taller-equipos/{taller_equipo_id}/estatus")
async def update_taller_equipo_estatus(
    taller_equipo_id: str,
    payload: EstatusUpdateRequest,
    authorization: Optional[str] = Header(None),
):
    """Corrección manual del estatus de un equipo en taller. SOLO administradores.
    Permite cambio libre entre los 4 estatus válidos. Registra bitácora del cambio."""
    current_user = await get_current_user(authorization)
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden corregir el estatus del taller")

    nuevo = (payload.estatus or "").strip()
    if nuevo not in VALID_TALLER_ESTATUS:
        raise HTTPException(status_code=400, detail=f"Estatus inválido. Válidos: {', '.join(VALID_TALLER_ESTATUS)}")

    equipo = await db.taller_equipos.find_one({"taller_equipo_id": taller_equipo_id}, {"_id": 0})
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado en taller")

    anterior = equipo.get("estatus", "")
    now_iso = datetime.now(timezone.utc).isoformat()
    set_fields = {"estatus": nuevo, "updated_at": now_iso}
    # fecha_entrega: se registra al pasar a 'Entregado', se limpia al salir de ese estatus.
    if nuevo == "Entregado":
        set_fields["fecha_entrega"] = equipo.get("fecha_entrega") or now_iso
    else:
        set_fields["fecha_entrega"] = None

    await db.taller_equipos.update_one({"taller_equipo_id": taller_equipo_id}, {"$set": set_fields})

    try:
        await db.bitacora.insert_one({
            "entry_type": "taller_estatus_corregido",
            "taller_equipo_id": taller_equipo_id,
            "serial": equipo.get("serial", ""),
            "modelo": equipo.get("modelo", ""),
            "client_id": equipo.get("client_id", ""),
            "estatus_anterior": anterior,
            "estatus_nuevo": nuevo,
            "motivo": (payload.motivo or "").strip(),
            "usuario": current_user.get("email", ""),
            "usuario_nombre": current_user.get("full_name", current_user.get("email", "")),
            "timestamp": now_iso,
        })
    except Exception as e:  # noqa: BLE001
        logger.error(f"[taller-estatus] no se pudo registrar bitácora: {e}")

    logger.info(f"Taller {taller_equipo_id}: estatus '{anterior}' → '{nuevo}' por {current_user.get('email')}")
    return {"success": True, "estatus_anterior": anterior, "estatus_nuevo": nuevo}


@router.delete("/taller-equipos/{taller_equipo_id}")
async def delete_taller_equipo(taller_equipo_id: str, authorization: Optional[str] = Header(None)):
    """Eliminar un equipo del taller de reparaciones. Solo administradores."""
    current_user = await get_current_user(authorization)
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar registros del taller")

    equipo = await db.taller_equipos.find_one({"taller_equipo_id": taller_equipo_id}, {"_id": 0})
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado en taller")

    await db.taller_equipos.delete_one({"taller_equipo_id": taller_equipo_id})
    logger.info(f"Equipo taller {taller_equipo_id} eliminado por {current_user.get('email')}")
    return {"message": "Registro de taller eliminado exitosamente"}
