"""Mantenimiento Masivo de Sucursales (Función Especial clientes:mantenimiento_masivo)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from config import db, get_current_user
from services.client_hierarchy import (
    adopt_orphan_branches,
    prepare_client_data,
    propagate_rif,
)

router = APIRouter()

MASS_PERMISSION = "clientes:mantenimiento_masivo"  # FN_SUCURSALES_MANTENIMIENTO_MASIVO
BRAND_MASS_PERMISSION = "marcas:mantenimiento_masivo"  # FN_MARCAS_MANTENIMIENTO_MASIVO
ACTIVE_PROJECT_EXCLUDED = ["Anulado", "Culminado"]
QUOTE_BLOCKING = ["Aprobada", "Configurada", "Enviada a Imple", "Facturada", "Pagada", "Entregada"]
SIMPLE_ACTIONS = {
    "segment": ["segment"],
    "ejecutivo": ["ejecutivo_user_id"],
    "categoria": ["categoria_comercial"],
    "tipo_servicio": ["tipo_servicio"],
    "coord_impl": ["coordinator_user_id", "implementer_user_id"],
    "integrador": ["integrador_id", "aplicativo"],
}


SEGMENTS = ["Pymes", "Corporativo", "Emprendedor", "Mixto"]
TIPOS_SERVICIO = ["VPOS", "MPOS", "Payment Gateway", "Link de Pago"]
MAX_BATCH = 3000


class MassActionRequest(BaseModel):
    action: str
    client_ids: list[str]
    payload: dict = {}


async def _require_mass(authorization, permission: str = MASS_PERMISSION):
    user = await get_current_user(authorization)
    if user.get("role") != "admin" and permission not in (user.get("special_permissions") or []):
        raise HTTPException(status_code=403, detail="Requiere la Función Especial: Mantenimiento Masivo")
    return user


async def _user_name(uid):
    if not uid:
        return ""
    u = await db.users.find_one({"user_id": uid}, {"_id": 0, "full_name": 1, "name": 1})
    if not u:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")
    return u.get("full_name") or u.get("name") or ""


async def _dependencies(c: dict) -> list[str]:
    cid = c["client_id"]
    reasons = []
    if await db.projects.count_documents({"$or": [{"client_id": cid}, {"rifs.client_id": cid}], "status": {"$nin": ACTIVE_PROJECT_EXCLUDED}}):
        reasons.append("Proyecto en ejecución")
    if await db.quotes.count_documents({"client_id": cid, "quote_status": {"$in": QUOTE_BLOCKING}}):
        reasons.append("Cotización aprobada")
    if await db.taller_equipos.count_documents({"client_id": cid, "estatus": {"$ne": "Entregado"}}):
        reasons.append("Orden de taller activa")
    if not c.get("is_branch") and await db.clients.count_documents({"parent_client_id": cid}):
        reasons.append("Tiene sucursales asociadas")
    return reasons


async def _build_set(action: str, p: dict) -> dict:
    if action == "segment":
        if p.get("segment") not in SEGMENTS:
            raise HTTPException(status_code=400, detail="Seleccione el segmento")
        return {"segment": p["segment"]}
    if action == "categoria":
        if not p.get("categoria_comercial") or not await db.commercial_categories.find_one({"name": p["categoria_comercial"]}, {"_id": 1}):
            raise HTTPException(status_code=400, detail="Seleccione una categoría comercial válida")
        return {"categoria_comercial": p["categoria_comercial"]}
    if action == "tipo_servicio":
        if not p.get("tipo_servicio") or any(t not in TIPOS_SERVICIO for t in p["tipo_servicio"]):
            raise HTTPException(status_code=400, detail="Seleccione el tipo de servicio")
        return {"tipo_servicio": list(p["tipo_servicio"])}
    if action == "ejecutivo":
        if not p.get("ejecutivo_user_id"):
            raise HTTPException(status_code=400, detail="Seleccione el ejecutivo")
        return {"ejecutivo_user_id": p["ejecutivo_user_id"], "ejecutivo_propietario": await _user_name(p["ejecutivo_user_id"])}
    if action == "coord_impl":
        out = {}
        if p.get("apply_coordinator"):
            out.update(coordinator_user_id=p.get("coordinator_user_id") or "", coordinator_name=await _user_name(p.get("coordinator_user_id")))
        if p.get("apply_implementer"):
            out.update(implementer_user_id=p.get("implementer_user_id") or "", implementer_name=await _user_name(p.get("implementer_user_id")))
        if not out:
            raise HTTPException(status_code=400, detail="Marque al menos un campo para aplicar")
        return out
    if action == "integrador":
        intg = await db.integrators.find_one({"integrator_id": p.get("integrador_id")}, {"_id": 0, "integrator_id": 1, "name": 1, "app_name": 1})
        if not intg or not (intg.get("app_name") or "").strip():
            raise HTTPException(status_code=400, detail="Seleccione el integrador y el aplicativo")
        return {"integrador_id": intg["integrator_id"], "integrador_name": intg["name"], "aplicativo": intg["app_name"]}
    raise HTTPException(status_code=400, detail="Acción no soportada")


@router.post("/clients/mass-action")
async def clients_mass_action(req: MassActionRequest, authorization: str | None = Header(None)):
    await _require_mass(authorization)
    ids = list(dict.fromkeys(req.client_ids or []))
    if not ids:
        raise HTTPException(status_code=400, detail="Seleccione al menos una sucursal")
    if len(ids) > MAX_BATCH:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_BATCH} registros por lote")
    docs = await db.clients.find({"client_id": {"$in": ids}}, {"_id": 0}).to_list(len(ids))
    updated, skipped = [], []
    label = lambda c: f"{c.get('rif', '')} {c.get('legal_name', '')} — {c.get('sucursal') or 'Principal'}".strip()

    if req.action == "delete":
        if (req.payload.get("confirm") or "") != "ELIMINAR":
            raise HTTPException(status_code=400, detail="Debe escribir ELIMINAR para confirmar")
        # Sucursales primero: un Principal puede quedar libre si sus sucursales también están en el lote
        for c in sorted(docs, key=lambda d: not d.get("is_branch")):
            reasons = await _dependencies(c)
            if reasons:
                skipped.append({"client_id": c["client_id"], "label": label(c), "reasons": reasons})
                continue
            await db.clients.delete_one({"client_id": c["client_id"]})
            updated.append(c["client_id"])
        return {"action": "delete", "processed": len(updated), "skipped": skipped}

    if req.action == "group_brand":
        brand = await db.brands.find_one({"brand_id": req.payload.get("marca_id")}, {"_id": 0})
        if not brand or not req.payload.get("grupo_economico_id") or brand.get("group_id") != req.payload["grupo_economico_id"]:
            raise HTTPException(status_code=400, detail="Seleccione un Grupo Económico y una Marca de ese grupo")
        for c in docs:
            if c.get("is_branch"):
                skipped.append({"client_id": c["client_id"], "label": label(c), "reasons": ["Hereda la Marca de su Tienda Principal"]})
                continue
            data = {**c, "marca_id": brand["brand_id"]}
            await prepare_client_data(data)
            await db.clients.update_one({"client_id": c["client_id"]}, {"$set": {k: data.get(k) for k in (
                "marca_id", "marca_name", "fantasy_name", "grupo_economico_id", "grupo_economico", "inherit_overrides",
                "segment", "categoria_comercial", "tipo_servicio", "aplicativo", "modelo_impresora_fiscal",
                "ejecutivo_user_id", "ejecutivo_propietario", "coordinator_user_id", "coordinator_name",
                "implementer_user_id", "implementer_name", "integrador_id", "integrador_name")}})
            await propagate_rif(await db.clients.find_one({"client_id": c["client_id"]}, {"_id": 0}))
            updated.append(c["client_id"])
        return {"action": req.action, "processed": len(updated), "skipped": skipped}

    if req.action not in SIMPLE_ACTIONS:
        raise HTTPException(status_code=400, detail="Acción no soportada")
    to_set = await _build_set(req.action, req.payload)
    units = [u for u in SIMPLE_ACTIONS[req.action] if u in to_set]
    for c in docs:
        ovr = list(dict.fromkeys((c.get("inherit_overrides") or []) + units))
        await db.clients.update_one({"client_id": c["client_id"]}, {"$set": {**to_set, "inherit_overrides": ovr}})
        if not c.get("is_branch"):
            await propagate_rif(await db.clients.find_one({"client_id": c["client_id"]}, {"_id": 0}))
        updated.append(c["client_id"])
    return {"action": req.action, "processed": len(updated), "skipped": skipped}


__all__ = ["adopt_orphan_branches", "router"]


class BrandMassActionRequest(BaseModel):
    action: str
    brand_ids: list[str]
    payload: dict = {}


@router.post("/marcas/mass-action")
async def brands_mass_action(req: BrandMassActionRequest, authorization: str | None = Header(None)):
    """Acciones masivas sobre Marcas: el valor queda en la Marca; RIF y sucursales lo heredan
    salvo los campos que tengan sobrescritos localmente (inherit_overrides)."""
    from services.client_hierarchy import propagate_brand
    await _require_mass(authorization, BRAND_MASS_PERMISSION)
    ids = list(dict.fromkeys(req.brand_ids or []))
    if not ids:
        raise HTTPException(status_code=400, detail="Seleccione al menos una marca")
    if len(ids) > MAX_BATCH:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_BATCH} marcas por lote")
    brands = await db.brands.find({"brand_id": {"$in": ids}}, {"_id": 0}).to_list(len(ids))
    updated, skipped = [], []
    found = {b["brand_id"] for b in brands}
    skipped += [{"client_id": i, "label": i, "reasons": ["Marca no encontrada"]} for i in ids if i not in found]
    now = datetime.now(UTC).isoformat()

    if req.action == "delete":
        if (req.payload.get("confirm") or "") != "ELIMINAR":
            raise HTTPException(status_code=400, detail="Debe escribir ELIMINAR para confirmar")
        for b in brands:
            n = await db.clients.count_documents({"marca_id": b["brand_id"]})
            if n:
                skipped.append({"client_id": b["brand_id"], "label": b["name"], "reasons": [f"Tiene {n} RIF/sucursal(es) asociado(s)"]})
                continue
            await db.brands.delete_one({"brand_id": b["brand_id"]})
            updated.append(b["brand_id"])
        return {"action": "delete", "processed": len(updated), "skipped": skipped}

    if req.action == "group":
        gid = req.payload.get("grupo_economico_id")
        if not gid or not await db.economic_groups.find_one({"group_id": gid}, {"_id": 1}):
            raise HTTPException(status_code=400, detail="Seleccione un Grupo Económico válido")
        for b in brands:
            await db.brands.update_one({"brand_id": b["brand_id"]}, {"$set": {"group_id": gid, "updated_at": now}})
            await propagate_brand(b["brand_id"], only_fields=())
            updated.append(b["brand_id"])
        return {"action": req.action, "processed": len(updated), "skipped": skipped}

    if req.action not in SIMPLE_ACTIONS or req.action == "tipo_servicio":
        raise HTTPException(status_code=400, detail="Acción no soportada")
    to_set = await _build_set(req.action, req.payload)
    for b in brands:
        chars = {**(b.get("characteristics") or {}), **to_set}
        await db.brands.update_one({"brand_id": b["brand_id"]}, {"$set": {"characteristics": chars, "updated_at": now}})
        await propagate_brand(b["brand_id"], only_fields=to_set.keys())
        updated.append(b["brand_id"])
    return {"action": req.action, "processed": len(updated), "skipped": skipped}


async def migrate_rbac_clientes_menu() -> dict:
    """Única vez: grupo de menú 'Clientes' y módulo 'Marcas' heredan lo que ya tenía cada perfil/usuario."""
    from datetime import datetime
    key = "rbac_clientes_menu_v1"
    if await db["_migrations"].find_one({"_id": key}):
        return {"skipped": True}
    n = 0
    for coll in ("profiles", "users"):
        async for d in db[coll].find({}, {"_id": 1, "menu_groups": 1, "permissions": 1}):
            upd = {}
            mg = d.get("menu_groups") or {}
            if mg and "clientes_menu" not in mg:
                upd["menu_groups.clientes_menu"] = bool(mg.get("gestion_comercial", True))
            perms = d.get("permissions") or {}
            if isinstance(perms, dict) and perms and "marcas" not in perms:
                upd["permissions.marcas"] = perms.get("clientes", "none")
            if upd:
                await db[coll].update_one({"_id": d["_id"]}, {"$set": upd})
                n += 1
    await db["_migrations"].update_one({"_id": key}, {"$set": {"applied_at": datetime.now(UTC).isoformat(), "docs": n}}, upsert=True)
    return {"docs": n}
