"""Route module: brands.py — Nivel 2 'Marca o Nombre Comercial' (Nombre de Fantasía)."""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header

from config import db, get_current_user, require_permission
from models import BrandCreate
from services.client_hierarchy import (
    brand_name_regex, clean_characteristics, propagate_brand, brand_inheritance, migrate_brands,
)

router = APIRouter()


def _contacts_count(doc: dict) -> int:
    return len([c for c in (doc.get("contacts") or []) if (c.get("email") or "").strip()])


async def _brand_rows(query: dict) -> list:
    brands = await db.brands.find(query, {"_id": 0}).sort("name", 1).to_list(20000)
    gids = list({b.get("group_id") for b in brands if b.get("group_id")})
    gmap = {g["group_id"]: g["name"] for g in await db.economic_groups.find(
        {"group_id": {"$in": gids}}, {"_id": 0, "group_id": 1, "name": 1}).to_list(10000)}
    agg = {r["_id"]: r for r in await db.clients.aggregate([
        {"$match": {"is_branch": {"$ne": True}, "marca_id": {"$in": [b["brand_id"] for b in brands]}}},
        {"$group": {"_id": "$marca_id", "n": {"$sum": 1}, "segs": {"$addToSet": "$segment"},
                    "ejs": {"$addToSet": {"id": "$ejecutivo_user_id", "name": "$ejecutivo_propietario"}}}},
    ]).to_list(None)}

    def _filters(b):
        # Valores para filtros: los de la Marca + los de sus RIF (lo que efectivamente tiene la marca).
        ch, a = b.get("characteristics") or {}, agg.get(b["brand_id"], {})
        segs = {s for s in [ch.get("segment"), *a.get("segs", [])] if s}
        ejs = {(e.get("id") or e.get("name")): e.get("name") or e.get("id")
               for e in [{"id": ch.get("ejecutivo_user_id"), "name": ch.get("ejecutivo_propietario")}, *a.get("ejs", [])]
               if e.get("id") or e.get("name")}
        return sorted(segs), [{"id": k, "name": v} for k, v in ejs.items()]

    rows = []
    for b in brands:
        segs, ejs = _filters(b)
        rows.append({
            "brand_id": b["brand_id"], "name": b["name"], "group_id": b.get("group_id"),
            "group_name": gmap.get(b.get("group_id")), "description": b.get("description") or "",
            "rif_count": agg.get(b["brand_id"], {}).get("n", 0), "contacts_count": _contacts_count(b),
            "characteristics_count": len([k for k in (b.get("characteristics") or {}) if not k.endswith(("_name", "_propietario"))]),
            "segments": segs, "ejecutivos": ejs,
        })
    return rows


@router.get("/marcas")
async def list_brands(search: str = "", group_id: str = "", authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    query = {}
    if search.strip():
        query["name"] = {"$regex": re.escape(search.strip()), "$options": "i"}
    if group_id == "_none_":
        query["group_id"] = {"$in": [None, ""]}
    elif group_id:
        query["group_id"] = group_id
    return await _brand_rows(query)


@router.get("/grupos-economicos/{group_id}/marcas")
async def list_group_brands(group_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    return await _brand_rows({"group_id": group_id})


async def _validate(payload: BrandCreate, brand_id: Optional[str] = None) -> dict:
    name = " ".join((payload.name or "").split())
    if not name:
        raise HTTPException(status_code=400, detail="El nombre de la Marca es obligatorio")
    q = {"name": brand_name_regex(name)}
    if brand_id:
        q["brand_id"] = {"$ne": brand_id}
    if await db.brands.find_one(q, {"_id": 0, "brand_id": 1}):
        raise HTTPException(status_code=400, detail=f"Ya existe una Marca con el nombre '{name}'")
    gid = (payload.group_id or "").strip() or None
    if gid and not await db.economic_groups.find_one({"group_id": gid}, {"_id": 0, "group_id": 1}):
        raise HTTPException(status_code=400, detail="Grupo Económico no encontrado")
    data = payload.model_dump()
    data.update({"name": name, "group_id": gid, "characteristics": clean_characteristics(payload.characteristics)})
    for c in data.get("contacts", []):
        if not c.get("contact_id"):
            c["contact_id"] = f"cnt_{uuid.uuid4().hex[:8]}"
    data["contacts"] = [c for c in data.get("contacts", []) if (c.get("full_name") or "").strip() or (c.get("email") or "").strip()]
    return data


@router.post("/marcas")
async def create_brand(payload: BrandCreate, authorization: Optional[str] = Header(None)):
    await require_permission(authorization, "marcas", "edit")
    data = await _validate(payload)
    brand = {"brand_id": f"mrc_{uuid.uuid4().hex[:12]}", **data,
             "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": None}
    await db.brands.insert_one(dict(brand))
    brand.pop("_id", None)
    return brand


@router.get("/marcas/{brand_id}")
async def get_brand(brand_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    b = await db.brands.find_one({"brand_id": brand_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    return b


@router.get("/marcas/{brand_id}/inheritance")
async def get_brand_inheritance(brand_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    b = await db.brands.find_one({"brand_id": brand_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    return await brand_inheritance(b)


@router.get("/marcas/{brand_id}/rifs")
async def get_brand_rifs(brand_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    rifs = await db.clients.find(
        {"marca_id": brand_id, "is_branch": {"$ne": True}},
        {"_id": 0, "client_id": 1, "rif": 1, "legal_name": 1, "sucursal": 1, "condicion": 1, "contacts": 1},
    ).sort("legal_name", 1).to_list(5000)
    counts = {r["_id"]: r["n"] for r in await db.clients.aggregate([
        {"$match": {"parent_client_id": {"$in": [r["client_id"] for r in rifs]}}},
        {"$group": {"_id": "$parent_client_id", "n": {"$sum": 1}}},
    ]).to_list(None)}
    return [{
        "client_id": r["client_id"], "rif": r.get("rif"), "legal_name": r.get("legal_name"),
        "sucursal": r.get("sucursal") or "Principal", "condicion": r.get("condicion"),
        "contacts_count": _contacts_count(r), "branches_count": counts.get(r["client_id"], 0),
    } for r in rifs]


@router.put("/marcas/{brand_id}")
async def update_brand(brand_id: str, payload: BrandCreate, authorization: Optional[str] = Header(None)):
    await require_permission(authorization, "marcas", "edit")
    existing = await db.brands.find_one({"brand_id": brand_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    data = await _validate(payload, brand_id)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.brands.update_one({"brand_id": brand_id}, {"$set": data})
    await propagate_brand(brand_id, old_name=existing.get("name"))
    return await get_brand(brand_id, authorization)


@router.delete("/marcas/{brand_id}")
async def delete_brand(brand_id: str, authorization: Optional[str] = Header(None)):
    await require_permission(authorization, "marcas", "edit")
    if not await db.brands.find_one({"brand_id": brand_id}, {"_id": 0, "brand_id": 1}):
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    n = await db.clients.count_documents({"marca_id": brand_id, "is_branch": {"$ne": True}})
    if n:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar la Marca porque tiene {n} RIF(s) asociado(s). Reasígnelos primero.")
    await db.brands.delete_one({"brand_id": brand_id})
    return {"deleted": True, "brand_id": brand_id}


@router.post("/admin/clients/migrate-brands")
async def run_brand_migration(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    return await migrate_brands(force=True)
