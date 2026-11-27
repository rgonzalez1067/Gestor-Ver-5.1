"""Multiproyectos: consolida 2+ cotizaciones activas (por Grupo, Marca o RIF) en UN proyecto Multi-RIF.

- Elegibles: cotizaciones no archivadas, no enviadas a Implementación y sin proyecto vinculado.
- Crea el proyecto con la estructura RIF → Sucursal (una sucursal por cotización / sucursal origen).
- Los equipos preasignados en Almacén se conservan agrupados por RIF y sucursal (`equipments_by_rif`).
- Todas las cotizaciones quedan marcadas "Enviada a Imple" y pasan al Histórico con comentario.
- Relación 1:N en `proyecto_cotizaciones` (cotizacion_id ÚNICO).
"""
import copy
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from config import db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()
ELIGIBLE_STATUSES = ["Aprobada", "Configurada", "Facturada", "Pagada", "Pagada Parcial"]
LEVEL_FIELD = {"grupo": "grupo_economico", "marca": "fantasy_name", "rif": "client_id"}


def _uname(u):
    return f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("email", "")


async def _linked_quote_ids() -> set:
    ids = set(await db.proyecto_cotizaciones.distinct("cotizacion_id"))
    ids |= set(q for q in await db.projects.distinct("quote_id") if q)
    return ids


@router.get("/multiprojects/entities")
async def multiproject_entities(level: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    if level not in LEVEL_FIELD:
        raise HTTPException(400, "Nivel inválido (grupo, marca o rif)")
    if level == "rif":
        cl = await db.clients.find({}, {"_id": 0, "client_id": 1, "rif": 1, "legal_name": 1}).to_list(10000)
        return {"items": sorted([{"value": c["client_id"], "label": f"{c.get('rif', '')} — {c.get('legal_name', '')}"} for c in cl],
                                key=lambda x: x["label"])}
    vals = [v for v in await db.clients.distinct(LEVEL_FIELD[level]) if v and str(v).strip()]
    return {"items": [{"value": v, "label": v} for v in sorted(vals, key=lambda s: str(s).lower())]}


async def _eligible_quotes(client_ids: list, only_ids: Optional[list] = None) -> list:
    linked = await _linked_quote_ids()
    flt = {"client_id": {"$in": client_ids}, "archived": {"$ne": True}, "quote_status": {"$in": ELIGIBLE_STATUSES},
           "sent_to_implementation_at": {"$in": [None, ""]}}
    if only_ids is not None:
        flt["quote_id"] = {"$in": only_ids}
    quotes = await db.quotes.find(flt, {"_id": 0}).sort("created_at", 1).to_list(500)
    return [q for q in quotes if q["quote_id"] not in linked]


async def _clients_for(level: str, value: str) -> dict:
    if level not in LEVEL_FIELD:
        raise HTTPException(400, "Nivel inválido (grupo, marca o rif)")
    cl = await db.clients.find({LEVEL_FIELD[level]: value}, {"_id": 0}).to_list(5000)
    return {c["client_id"]: c for c in cl}


async def _equip_by_quote(quote_ids: list) -> dict:
    out = {}
    async for a in db.serial_assignments.find({"quote_id": {"$in": quote_ids}, "status": {"$in": ["preasignado", "asignado"]}}, {"_id": 0}):
        out.setdefault(a["quote_id"], []).append(a)
    return out


_PH = ["Recibido", "Configurado", "Testeado", "En Producción"]


def _quote_matrix(q: dict) -> dict:
    """Matriz banco → producto propia de cada cotización (misma regla que el envío individual)."""
    m = {}
    if (q.get("quote_type") or "").upper() in ("GATEWAY", "LINK_PAGO"):
        for it in q.get("pg_setup_items") or []:
            bn, name = (it.get("banco") or "").strip(), (it.get("concepto") or "").strip()
            if bn and name and bn.upper() != "N/A":
                m.setdefault(bn, {})[name] = {ph: {"expected": 1, "processed": 0, "completed": False} for ph in _PH}
    else:
        for it in q.get("services") or []:
            if it.get("item_type") == "additional" and it.get("bank_name") and it.get("item_name"):
                m.setdefault(it["bank_name"], {}).setdefault(it["item_name"], {})
    return m


def _quote_summary(q: dict, c: dict, store: str, boxes: int) -> dict:
    return {"quote_id": q["quote_id"], "quote_number": q.get("quote_number"), "quote_type": q.get("quote_type"),
            "store_name": store, "box_count": boxes, "client_name": c.get("legal_name") or q.get("client_name"),
            "client": {k: c.get(k) for k in ("rif", "legal_name", "fantasy_name", "address")},
            "services": [x for x in q.get("services") or [] if x.get("item_type") == "additional"],
            "pg_setup_items": q.get("pg_setup_items") or [],
            "banks": sorted({x.get("bank_name") for x in q.get("services") or [] if x.get("bank_name")} |
                            {(x.get("banco") or "").strip() for x in q.get("pg_setup_items") or [] if (x.get("banco") or "").strip() not in ("", "N/A")})}


def _store_name(q: dict) -> str:
    b = (q.get("branch_details") or [{}])[0] if q.get("branch_details") else {}
    return b.get("store_name") or q.get("store_name") or "Sede Principal"


@router.get("/multiprojects/search")
async def multiproject_search(level: str, value: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    clients = await _clients_for(level, value)
    quotes = await _eligible_quotes(list(clients))
    eq = await _equip_by_quote([q["quote_id"] for q in quotes])
    return {"quotes": [{
        "quote_id": q["quote_id"], "quote_number": q.get("quote_number"), "quote_status": q.get("quote_status"),
        "quote_type": q.get("quote_type") or q.get("business_type"), "client_id": q.get("client_id"),
        "client_name": clients.get(q["client_id"], {}).get("legal_name") or q.get("client_name"),
        "rif": clients.get(q["client_id"], {}).get("rif"), "fantasy_name": clients.get(q["client_id"], {}).get("fantasy_name"),
        "store_name": _store_name(q), "total_usd": q.get("total_usd", 0), "equipment_count": len(eq.get(q["quote_id"], [])),
    } for q in quotes]}


class MPRequest(BaseModel):
    quote_ids: List[str]
    implementation_instructions: Optional[str] = None
    server_name: Optional[str] = None


async def _build(quote_ids: list):
    if len(set(quote_ids)) < 2:
        raise HTTPException(400, "Seleccione al menos 2 cotizaciones")
    raw = await db.quotes.find({"quote_id": {"$in": quote_ids}}, {"_id": 0, "client_id": 1}).to_list(500)
    clients = {c["client_id"]: c for c in await db.clients.find({"client_id": {"$in": [r["client_id"] for r in raw]}}, {"_id": 0}).to_list(500)}
    quotes = await _eligible_quotes(list(clients), quote_ids)
    if len(quotes) != len(set(quote_ids)):
        raise HTTPException(400, "Alguna cotización ya no es elegible (enviada, archivada o vinculada a otro proyecto)")
    eq = await _equip_by_quote(quote_ids)
    tree, dist, summaries = {}, {}, []
    for q in quotes:
        c = clients.get(q["client_id"], {})
        boxes = int(q.get("box_count") or sum(int(b.get("quantity") or 0) for b in q.get("branch_details") or []) or 1)
        store = f"{_store_name(q)} ({q.get('quote_number')})"
        r = dist.setdefault(q["client_id"], {"client_id": q["client_id"], "rif": c.get("rif"), "client_name": c.get("legal_name") or q.get("client_name"),
                                             "boxes": 0, "stores": []})
        r["boxes"] += boxes
        r["stores"].append({"name": store, "boxes": boxes, "implementation_matrix": _quote_matrix(q)})
        summaries.append(_quote_summary(q, c, store, boxes))
        g = tree.setdefault(c.get("grupo_economico") or "Sin Grupo Económico", {})
        m = g.setdefault(c.get("fantasy_name") or "Sin Marca", {})
        rr = m.setdefault(q["client_id"], {"rif": c.get("rif"), "client_name": r["client_name"], "stores": []})
        rr["stores"].append({"store_name": store, "quote_id": q["quote_id"], "quote_number": q.get("quote_number"),
                             "box_count": boxes, "equipments": [{"modelo": a.get("item_name"), "serial": a.get("serial"),
                                                                 "warehouse_id": a.get("warehouse_id")} for a in eq.get(q["quote_id"], [])]})
    whs = {w["warehouse_id"]: w["name"] for w in await db.warehouses.find({}, {"_id": 0, "warehouse_id": 1, "name": 1}).to_list(200)}
    by_rif = []
    for g, marcas in tree.items():
        for m, rifs in marcas.items():
            for cid, rr in rifs.items():
                for st in rr["stores"]:
                    for e in st["equipments"]:
                        e["origen"] = whs.get(e.pop("warehouse_id", None), "Almacén")
                by_rif.append({"client_id": cid, "grupo": g, "marca": m, **rr,
                               "equipment_count": sum(len(s["equipments"]) for s in rr["stores"])})
    level = "Multi-Grupo" if len(tree) > 1 else "Multi-Marca" if len({(g, m) for g, ms in tree.items() for m in ms}) > 1 else \
        "Multi-RIF / Multi-Tienda" if len(dist) > 1 else "Multi-Tienda"
    return quotes, clients, list(dist.values()), by_rif, level, summaries


@router.post("/multiprojects/preview")
async def multiproject_preview(body: MPRequest, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    _, _, _, by_rif, level, summaries = await _build(body.quote_ids)
    return {"level": level, "rifs": by_rif, "summaries": summaries, "total_equipments": sum(r["equipment_count"] for r in by_rif)}


@router.post("/multiprojects/create")
async def multiproject_create(body: MPRequest, authorization: Optional[str] = Header(None)):
    from routes.quote_history import archive_quote_to_history
    from routes.quote_transitions import _create_project_from_quote
    user = await get_current_user(authorization)
    quotes, clients, dist, by_rif, level, summaries = await _build(body.quote_ids)
    primary = quotes[0]
    pc = clients.get(primary["client_id"], {})
    now = datetime.now(timezone.utc).isoformat()
    equipments = [{"modelo": e["modelo"], "serial": e["serial"], "rif": r["rif"], "store_name": s["store_name"], "quote_number": s["quote_number"]}
                  for r in by_rif for s in r["stores"] for e in s["equipments"]]
    numbers = [q.get("quote_number") for q in quotes]

    # 1) Marcar todas como Enviadas a Imple y archivarlas en el Histórico (comentario Multiproyecto)
    for q in quotes:
        await db.quotes.update_one({"quote_id": q["quote_id"]}, {"$set": {"quote_status": "Enviada a Imple", "sent_to_implementation_at": now,
                                                                          "multiproject_comment": f"Enviada a Implementación en Multiproyecto junto a: {', '.join(n for n in numbers if n != q.get('quote_number'))}"}})
        await archive_quote_to_history(q["quote_id"], "status_enviada_imple", user)

    # 2) Proyecto único Multi-RIF a partir de la cotización principal
    synth = copy.deepcopy(primary)
    synth.update(is_multirif=True, multirif_distribution=dist, scope_tree=None, quote_status="Enviada a Imple", branch_details=[],
                 box_count=sum(r["boxes"] for r in dist),
                 total_usd=round(sum(float(q.get("total_usd") or 0) for q in quotes), 2),
                 total_bs=round(sum(float(q.get("total_bs") or 0) for q in quotes), 2),
                 # Servicios/bancos de TODAS las cotizaciones (la matriz global y la lista de bancos son la unión)
                 services=[x for q in quotes for x in q.get("services") or []],
                 pg_setup_items=[x for q in quotes for x in q.get("pg_setup_items") or []])
    await _create_project_from_quote(synth, primary["quote_id"], None, equipments or None, None, body.server_name, None,
                                     pc.get("grupo_economico") or "Sin Grupo Económico", pc.get("fantasy_name"), body.implementation_instructions)
    project = await db.projects.find_one({"quote_id": primary["quote_id"]}, {"_id": 0, "project_id": 1, "project_number": 1})
    if not project:
        raise HTTPException(500, "No se pudo crear el proyecto consolidado")
    pid, pnum = project["project_id"], project.get("project_number")
    await db.projects.update_one({"project_id": pid}, {"$set": {
        "is_multiproject": True, "multiproject_level": level, "quote_ids": [q["quote_id"] for q in quotes], "quote_numbers": numbers,
        "equipments_by_rif": by_rif, "quote_summaries": summaries, "multiproject_created_by": _uname(user), "multiproject_created_at": now}})
    for q in quotes:
        await db.proyecto_cotizaciones.insert_one({"proyecto_id": pid, "cotizacion_id": q["quote_id"], "quote_number": q.get("quote_number"),
                                                   "client_id": q.get("client_id"), "created_at": now, "created_by": user.get("user_id")})
        await db.quote_history.update_many({"quote_id": q["quote_id"]}, {"$set": {
            "multiproject_comment": f"Enviada en Multiproyecto {pnum} (consolidado con {len(quotes)} cotizaciones)",
            "project_id": pid, "project_number": pnum}})
    await db.serial_assignments.update_many({"quote_id": {"$in": [q["quote_id"] for q in quotes]}, "status": {"$in": ["preasignado", "asignado"]}},
                                            {"$set": {"project_id": pid, "project_number": pnum}})
    logger.info(f"[multiproject] {pnum}: {numbers} por {user.get('email')}")
    return {"project_id": pid, "project_number": pnum, "quotes": numbers, "level": level}


async def ensure_multiproject_indexes():
    await db.raw["proyecto_cotizaciones"].create_index("cotizacion_id", unique=True)
