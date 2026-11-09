"""Jerarquía de Clientes en 4 niveles: Grupo Económico → Marca → RIF → Sucursal.

Características: se materializan en los campos del RIF/Sucursal; `inherit_overrides`
lista las unidades definidas localmente (campo por campo). Grupo/Marca guardan sus
valores propios en `characteristics`.
Contactos: cada nivel guarda los propios; el efectivo es el del nivel más cercano
que tenga contactos (sobrescritura por bloque).
"""
import logging
import re
import uuid
from datetime import datetime, timezone

from config import db

logger = logging.getLogger(__name__)

# Unidades heredables: la 1ª clave decide si la unidad está definida.
INHERIT_UNITS = [
    ("segment",), ("categoria_comercial",), ("tipo_servicio",), ("aplicativo",),
    ("modelo_impresora_fiscal",),
    ("ejecutivo_user_id", "ejecutivo_propietario"),
    ("coordinator_user_id", "coordinator_name"),
    ("implementer_user_id", "implementer_name"),
    ("integrador_id", "integrador_name"),
]
UNIT_LABELS = {
    "segment": "Segmento", "categoria_comercial": "Categoría Comercial", "tipo_servicio": "Tipo de Servicio",
    "aplicativo": "Aplicativo", "modelo_impresora_fiscal": "Impresora Fiscal",
    "ejecutivo_user_id": "Ejecutivo Propietario", "coordinator_user_id": "Coordinador",
    "implementer_user_id": "Implementador", "integrador_id": "Integrador",
}
INHERIT_FIELDS = [f for u in INHERIT_UNITS for f in u]
LEVEL_LABELS = {"grupo": "Grupo Económico", "marca": "Marca", "principal": "RIF / Razón Social", "local": "Sucursal"}


def _empty(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and len(v) == 0)


def _norm(v):
    if isinstance(v, list):
        return sorted(str(x) for x in v)
    return v.strip() if isinstance(v, str) else v


def norm_brand_key(name: str) -> str:
    return " ".join((name or "").upper().split())


def brand_name_regex(name: str) -> dict:
    parts = [re.escape(p) for p in (name or "").split()]
    return {"$regex": r"^\s*" + r"\s+".join(parts) + r"\s*$", "$options": "i"}


def clean_characteristics(raw: dict) -> dict:
    raw = raw or {}
    out = {}
    for unit in INHERIT_UNITS:
        if _empty(raw.get(unit[0])):
            continue
        for f in unit:
            out[f] = raw.get(f)
    return out


def merge_effective(parent: tuple, own: dict, level: str, name: str) -> tuple:
    """parent=(values, sources). Devuelve (values, sources) aplicando lo propio por unidad."""
    p_vals, p_src = parent
    vals, src = dict(p_vals), dict(p_src)
    for unit in INHERIT_UNITS:
        if not _empty((own or {}).get(unit[0])):
            for f in unit:
                vals[f] = own.get(f)
            src[unit[0]] = {"level": level, "name": name}
    return vals, src


async def group_effective(group_id):
    if not group_id:
        return {}, {}
    g = await db.economic_groups.find_one({"group_id": group_id}, {"_id": 0, "name": 1, "characteristics": 1})
    if not g:
        return {}, {}
    return merge_effective(({}, {}), g.get("characteristics") or {}, "grupo", g.get("name"))


async def brand_effective(brand: dict):
    parent = await group_effective(brand.get("group_id"))
    return merge_effective(parent, brand.get("characteristics") or {}, "marca", brand.get("name"))


def compute_overrides(data: dict, parent_vals: dict) -> list:
    out = []
    for unit in INHERIT_UNITS:
        k = unit[0]
        if not _empty(data.get(k)) and _norm(data.get(k)) != _norm(parent_vals.get(k)):
            out.append(k)
    return out


def apply_inheritance(data: dict, parent_vals: dict, overrides: list) -> dict:
    """Rellena las unidades NO sobrescritas con el valor del padre. Retorna los cambios."""
    changes = {}
    for unit in INHERIT_UNITS:
        if unit[0] in overrides:
            continue
        for f in unit:
            new = parent_vals.get(f)
            if new is None and f == "tipo_servicio":
                new = []
            if f == "segment" and _empty(new):
                continue
            if _norm(data.get(f)) != _norm(new):
                changes[f] = new
    data.update(changes)
    return changes


async def _principal_of(client: dict):
    if client.get("is_branch") and client.get("parent_client_id"):
        p = await db.clients.find_one({"client_id": client["parent_client_id"]}, {"_id": 0})
        if p:
            return p
    return client


async def parent_values_for_client(client: dict) -> dict:
    """Valores efectivos del padre inmediato (Marca para un RIF; RIF para una Sucursal)."""
    if client.get("is_branch") and client.get("parent_client_id"):
        p = await db.clients.find_one({"client_id": client["parent_client_id"]}, {"_id": 0})
        return {f: (p or {}).get(f) for f in INHERIT_FIELDS}
    if client.get("marca_id"):
        b = await db.brands.find_one({"brand_id": client["marca_id"]}, {"_id": 0})
        if b:
            return (await brand_effective(b))[0]
    if client.get("grupo_economico_id"):
        return (await group_effective(client["grupo_economico_id"]))[0]
    return {}


async def prepare_client_data(data: dict, self_client_id=None):
    """Normaliza Marca/Grupo, nombre de fantasía y herencia de características."""
    is_branch = bool(data.get("is_branch") and data.get("parent_client_id"))
    if is_branch:
        p = await db.clients.find_one({"client_id": data["parent_client_id"]}, {"_id": 0})
        if p:
            data["marca_id"] = p.get("marca_id")
            data["marca_name"] = p.get("marca_name")
            data["grupo_economico_id"] = p.get("grupo_economico_id")
            data["grupo_economico"] = p.get("grupo_economico")
    else:
        mid = (data.get("marca_id") or "").strip() or None
        brand = await db.brands.find_one({"brand_id": mid}, {"_id": 0}) if mid else None
        if brand:
            data["marca_id"] = brand["brand_id"]
            data["marca_name"] = brand["name"]
            data["fantasy_name"] = brand["name"]
            gid = brand.get("group_id")
            g = await db.economic_groups.find_one({"group_id": gid}, {"_id": 0, "name": 1}) if gid else None
            data["grupo_economico_id"] = gid if g else None
            data["grupo_economico"] = g["name"] if g else None
        else:
            data["marca_id"] = None
            data["marca_name"] = None
    if _empty(data.get("fantasy_name")):
        data["fantasy_name"] = (data.get("marca_name") or data.get("legal_name") or "").strip()
    parent_vals = await parent_values_for_client(data)
    overrides = compute_overrides(data, parent_vals)
    apply_inheritance(data, parent_vals, overrides)
    if _empty(data.get("segment")):
        data["segment"] = "Pymes"
    data["inherit_overrides"] = overrides
    return data


async def propagate_rif(client: dict):
    """Re-aplica la herencia RIF → Sucursales."""
    parent_vals = {f: client.get(f) for f in INHERIT_FIELDS}
    sync = {k: client.get(k) for k in ("marca_id", "marca_name", "grupo_economico_id", "grupo_economico")}
    async for br in db.clients.find({"parent_client_id": client["client_id"]}, {"_id": 0}):
        changes = apply_inheritance(dict(br), parent_vals, br.get("inherit_overrides") or [])
        for k, v in sync.items():
            if br.get(k) != v:
                changes[k] = v
        if changes:
            await db.clients.update_one({"client_id": br["client_id"]}, {"$set": changes})


async def propagate_brand(brand_id: str, old_name=None):
    brand = await db.brands.find_one({"brand_id": brand_id}, {"_id": 0})
    if not brand:
        return
    vals, _ = await brand_effective(brand)
    gid = brand.get("group_id")
    g = await db.economic_groups.find_one({"group_id": gid}, {"_id": 0, "name": 1}) if gid else None
    sync = {"marca_name": brand["name"], "fantasy_name": brand["name"],
            "grupo_economico_id": gid if g else None, "grupo_economico": g["name"] if g else None}
    async for c in db.clients.find({"marca_id": brand_id, "is_branch": {"$ne": True}}, {"_id": 0}):
        changes = apply_inheritance(c, vals, c.get("inherit_overrides") or [])
        for k, v in sync.items():
            if c.get(k) != v:
                changes[k] = v
                c[k] = v
        if changes:
            await db.clients.update_one({"client_id": c["client_id"]}, {"$set": changes})
        await propagate_rif(c)
    if old_name and old_name != brand["name"]:
        await db.clients.update_many(
            {"marca_id": brand_id, "is_branch": True, "fantasy_name": old_name},
            {"$set": {"fantasy_name": brand["name"]}},
        )


async def propagate_group(group_id: str):
    async for b in db.brands.find({"group_id": group_id}, {"_id": 0, "brand_id": 1}):
        await propagate_brand(b["brand_id"])


# ==================== CONTACTOS ====================

def _contacts_with_email(doc: dict) -> list:
    return [c for c in ((doc or {}).get("contacts") or []) if (c.get("email") or "").strip()]


async def lineage(client: dict) -> list:
    """Niveles del cliente de abajo hacia arriba: [(scope, doc, name)]."""
    out = []
    principal = await _principal_of(client)
    if principal.get("client_id") != client.get("client_id"):
        out.append(("local", client, client.get("sucursal") or "Sucursal"))
    out.append(("principal", principal, principal.get("legal_name") or principal.get("rif")))
    gid = principal.get("grupo_economico_id")
    if principal.get("marca_id"):
        b = await db.brands.find_one({"brand_id": principal["marca_id"]}, {"_id": 0})
        if b:
            out.append(("marca", b, b.get("name")))
            gid = b.get("group_id") or gid
    if gid:
        g = await db.economic_groups.find_one({"group_id": gid}, {"_id": 0})
        if g:
            out.append(("grupo", g, g.get("name")))
    return out


async def lineage_contacts(client: dict):
    """Todos los contactos (con email) del árbol del cliente con su nivel de procedencia.
    `effective=True` marca los del nivel más cercano que define contactos."""
    levels = await lineage(client)
    effective_scope = next((s for s, d, _ in levels if _contacts_with_email(d)), None)
    out = []
    for scope, doc, name in levels:
        for c in _contacts_with_email(doc):
            item = dict(c)
            item["scope"] = scope
            item["level_label"] = LEVEL_LABELS[scope]
            item["level_name"] = name
            item["sucursal"] = doc.get("sucursal") or ("Principal" if scope == "principal" else LEVEL_LABELS[scope])
            item["effective"] = scope == effective_scope
            if scope == "grupo":
                item["grupo_economico_name"] = name
                item["source_group_id"] = doc.get("group_id")
            out.append(item)
    return out, levels, effective_scope


async def effective_contacts(client: dict) -> list:
    contacts, _, _ = await lineage_contacts(client)
    return [c for c in contacts if c.get("effective")]


def _display(vals: dict, unit: tuple):
    v = vals.get(unit[-1]) if len(unit) > 1 else vals.get(unit[0])
    if isinstance(v, list):
        return ", ".join(v)
    return v or ""


async def client_inheritance(client: dict) -> dict:
    """Valor efectivo y nivel de procedencia de cada característica + contactos del árbol."""
    principal = await _principal_of(client)
    is_branch = principal.get("client_id") != client.get("client_id")
    if principal.get("marca_id"):
        b = await db.brands.find_one({"brand_id": principal["marca_id"]}, {"_id": 0})
        base = await brand_effective(b) if b else ({}, {})
    else:
        base = await group_effective(principal.get("grupo_economico_id"))
    _, src = base
    p_ovr = principal.get("inherit_overrides") or []
    c_ovr = client.get("inherit_overrides") or [] if is_branch else []
    rows = []
    for unit in INHERIT_UNITS:
        k = unit[0]
        if is_branch and k in c_ovr:
            source = {"level": "local", "name": client.get("sucursal")}
        elif k in p_ovr:
            source = {"level": "principal", "name": principal.get("legal_name")}
        else:
            source = src.get(k)
        rows.append({
            "field": k, "label": UNIT_LABELS[k], "value": _display(client, unit),
            "source_level": (source or {}).get("level"),
            "source_label": LEVEL_LABELS.get((source or {}).get("level"), ""),
            "source_name": (source or {}).get("name"),
            "overridden": (k in c_ovr) if is_branch else (k in p_ovr),
        })
    contacts, levels, eff = await lineage_contacts(client)
    return {
        "client_id": client.get("client_id"),
        "levels": [{"scope": s, "label": LEVEL_LABELS[s], "name": n} for s, _, n in levels],
        "characteristics": rows,
        "contacts": contacts,
        "effective_contacts_scope": eff,
    }


async def brand_inheritance(brand: dict) -> dict:
    vals, src = await brand_effective(brand)
    g_vals, g_src = await group_effective(brand.get("group_id"))
    rows = []
    for unit in INHERIT_UNITS:
        k = unit[0]
        s = src.get(k) or {}
        rows.append({"field": k, "label": UNIT_LABELS[k], "value": _display(vals, unit),
                     "source_level": s.get("level"), "source_label": LEVEL_LABELS.get(s.get("level"), ""),
                     "source_name": s.get("name"), "overridden": s.get("level") == "marca"})
    g = await db.economic_groups.find_one({"group_id": brand.get("group_id")}, {"_id": 0}) if brand.get("group_id") else None
    contacts = []
    own = _contacts_with_email(brand)
    for scope, doc, name in (("marca", brand, brand.get("name")), ("grupo", g, (g or {}).get("name"))):
        for c in _contacts_with_email(doc):
            contacts.append({**c, "scope": scope, "level_label": LEVEL_LABELS[scope], "level_name": name,
                             "effective": (scope == "marca") if own else (scope == "grupo")})
    return {
        "brand_id": brand.get("brand_id"), "effective_values": vals, "group_values": g_vals,
        "group_sources": g_src, "characteristics": rows, "contacts": contacts,
        "effective_contacts_scope": "marca" if own else ("grupo" if g and _contacts_with_email(g) else None),
    }


# ==================== MIGRACIÓN ====================

MIGRATION_KEY = "client_brands_v1"


async def migrate_brands(force: bool = False) -> dict:
    """Crea una Marca por cada nombre de fantasía de los RIF (principales) sin marca y
    la enlaza al Grupo Económico de esos RIF. Idempotente."""
    if not force and await db["_migrations"].find_one({"_id": MIGRATION_KEY}):
        return {"skipped": True}
    groups = await db.economic_groups.find({}, {"_id": 0, "group_id": 1, "name": 1}).to_list(10000)
    g_by_id = {g["group_id"]: g for g in groups}
    g_by_name = {norm_brand_key(g["name"]): g["group_id"] for g in groups}
    brands = await db.brands.find({}, {"_id": 0, "brand_id": 1, "name": 1, "group_id": 1}).to_list(100000)
    b_by_key = {norm_brand_key(b["name"]): b for b in brands}

    buckets: dict = {}
    async for c in db.clients.find(
        {"is_branch": {"$ne": True}, "$or": [{"marca_id": {"$exists": False}}, {"marca_id": None}, {"marca_id": ""}]},
        {"_id": 0, "client_id": 1, "fantasy_name": 1, "grupo_economico_id": 1, "grupo_economico": 1},
    ):
        key = norm_brand_key(c.get("fantasy_name"))
        if not key:
            continue
        gid = c.get("grupo_economico_id") if c.get("grupo_economico_id") in g_by_id else None
        gid = gid or g_by_name.get(norm_brand_key(c.get("grupo_economico")))
        bk = buckets.setdefault(key, {"name": " ".join((c.get("fantasy_name") or "").split()), "ids": [], "groups": {}})
        bk["ids"].append(c["client_id"])
        if gid:
            bk["groups"][gid] = bk["groups"].get(gid, 0) + 1

    created = linked = conflicts = 0
    now = datetime.now(timezone.utc).isoformat()
    for key, bk in buckets.items():
        brand = b_by_key.get(key)
        if not brand:
            gid = max(bk["groups"], key=bk["groups"].get) if bk["groups"] else None
            conflicts += 1 if len(bk["groups"]) > 1 else 0
            brand = {"brand_id": f"mrc_{uuid.uuid4().hex[:12]}", "name": bk["name"], "group_id": gid,
                     "description": "", "characteristics": {}, "contacts": [], "created_at": now,
                     "updated_at": None, "migrated": True}
            await db.brands.insert_one(dict(brand))
            b_by_key[key] = brand
            created += 1
        gid = brand.get("group_id")
        gname = g_by_id.get(gid, {}).get("name") if gid else None
        await db.clients.update_many(
            {"client_id": {"$in": bk["ids"]}},
            {"$set": {"marca_id": brand["brand_id"], "marca_name": brand["name"],
                      "grupo_economico_id": gid, "grupo_economico": gname}},
        )
        linked += len(bk["ids"])

    # Overrides: RIF vs Marca; Sucursal vs RIF (preserva todos los valores actuales)
    ovr_rif = ovr_br = 0
    async for c in db.clients.find({"is_branch": {"$ne": True}, "inherit_overrides": {"$exists": False}}, {"_id": 0}):
        pv = await parent_values_for_client(c)
        await db.clients.update_one({"client_id": c["client_id"]}, {"$set": {"inherit_overrides": compute_overrides(c, pv)}})
        ovr_rif += 1
    async for br in db.clients.find({"is_branch": True}, {"_id": 0}):
        p = await db.clients.find_one({"client_id": br.get("parent_client_id")}, {"_id": 0})
        if not p:
            continue
        upd = {"marca_id": p.get("marca_id"), "marca_name": p.get("marca_name"),
               "grupo_economico_id": p.get("grupo_economico_id"), "grupo_economico": p.get("grupo_economico")}
        if "inherit_overrides" not in br:
            upd["inherit_overrides"] = compute_overrides(br, {f: p.get(f) for f in INHERIT_FIELDS})
            ovr_br += 1
        await db.clients.update_one({"client_id": br["client_id"]}, {"$set": upd})

    result = {"brands_created": created, "rifs_linked": linked, "group_conflicts": conflicts,
              "rif_overrides_computed": ovr_rif, "branch_overrides_computed": ovr_br}
    await db["_migrations"].update_one({"_id": MIGRATION_KEY}, {"$set": {"applied_at": now, **result}}, upsert=True)
    logger.info(f"Client brands migration: {result}")
    return result


# ==================== SUCURSALES HUÉRFANAS ====================

def _is_principal_name(sucursal) -> bool:
    return (sucursal or "Principal").strip().lower() == "principal"


async def adopt_orphan_branches(principal: dict) -> int:
    """Registros del mismo RIF con sucursal ≠ Principal que quedaron como independientes
    pasan a ser Sucursales del Principal y heredan su Marca/Grupo/características."""
    if principal.get("is_branch") or not _is_principal_name(principal.get("sucursal")):
        return 0
    n = 0
    async for o in db.clients.find({"rif": principal.get("rif"), "is_branch": {"$ne": True},
                                    "client_id": {"$ne": principal["client_id"]}}, {"_id": 0}):
        if _is_principal_name(o.get("sucursal")):
            continue
        old_brand = o.get("marca_id")
        pv = {f: principal.get(f) for f in INHERIT_FIELDS}
        upd = {"is_branch": True, "parent_client_id": principal["client_id"],
               "marca_id": principal.get("marca_id"), "marca_name": principal.get("marca_name"),
               "grupo_economico_id": principal.get("grupo_economico_id"),
               "grupo_economico": principal.get("grupo_economico"),
               "inherit_overrides": compute_overrides(o, pv)}
        await db.clients.update_one({"client_id": o["client_id"]}, {"$set": upd})
        n += 1
        # Marca creada solo para esta sucursal en la migración → se elimina si quedó vacía
        if old_brand and old_brand != principal.get("marca_id"):
            b = await db.brands.find_one({"brand_id": old_brand}, {"_id": 0, "migrated": 1, "contacts": 1, "characteristics": 1})
            if b and b.get("migrated") and not b.get("contacts") and not b.get("characteristics") \
                    and not await db.clients.count_documents({"marca_id": old_brand, "is_branch": {"$ne": True}}):
                await db.brands.delete_one({"brand_id": old_brand})
    return n


async def relink_orphan_branches() -> dict:
    key = "client_branches_relink_v1"
    if await db["_migrations"].find_one({"_id": key}):
        return {"skipped": True}
    adopted = 0
    rifs = await db.clients.aggregate([
        {"$match": {"is_branch": {"$ne": True}}},
        {"$group": {"_id": "$rif", "n": {"$sum": 1}}}, {"$match": {"n": {"$gt": 1}}},
    ]).to_list(None)
    for r in rifs:
        docs = await db.clients.find({"rif": r["_id"], "is_branch": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(None)
        principal = next((d for d in docs if _is_principal_name(d.get("sucursal"))), None)
        if principal:
            adopted += await adopt_orphan_branches(principal)
    res = {"rifs_checked": len(rifs), "branches_adopted": adopted}
    await db["_migrations"].update_one({"_id": key}, {"$set": {"applied_at": datetime.now(timezone.utc).isoformat(), **res}}, upsert=True)
    logger.info(f"Orphan branches relink: {res}")
    return res
