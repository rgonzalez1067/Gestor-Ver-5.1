"""Routes: /api/referentes — Catálogo maestro de Referentes (origen comercial de los Contactos Iniciales)."""
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from config import db, get_current_user
from routes.auth import _effective_special_permissions

router = APIRouter(tags=["referentes"])
CREATE_FLAG = "referentes:crear"


class TipoReferente(str, Enum):
    PERSONA = "PERSONA"
    AREA = "AREA"
    EMPRESA = "EMPRESA"


class ReferenteIn(BaseModel):
    nombre_referente: str = Field(..., min_length=1, max_length=150)
    tipo_referente: TipoReferente
    empresa: Optional[str] = Field("", max_length=150)
    persona: Optional[str] = Field("", max_length=150)


class ReferenteUpdate(BaseModel):
    nombre_referente: Optional[str] = Field(None, min_length=1, max_length=150)
    tipo_referente: Optional[TipoReferente] = None
    empresa: Optional[str] = Field(None, max_length=150)
    persona: Optional[str] = Field(None, max_length=150)
    estatus: Optional[bool] = None


class MergeIn(BaseModel):
    target_id: str
    source_ids: List[str] = Field(..., min_length=1)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def _is_admin(user: dict) -> bool:
    return (user.get("role") or "").lower() == "admin"


async def can_create_referente(user: dict) -> bool:
    return _is_admin(user) or CREATE_FLAG in await _effective_special_permissions(user)


async def _require_admin(authorization):
    from permissions_catalog import has_module_level
    user = await get_current_user(authorization)
    if not has_module_level(user, "referentes", "edit"):
        raise HTTPException(status_code=403, detail="No tiene permisos de Edición Total en el catálogo de Referentes")
    return user


async def create_or_get_referente(data: ReferenteIn, user: dict) -> dict:
    """Crea el referente o devuelve el existente si ya hay uno con el mismo nombre (duplicado exacto)."""
    name = re.sub(r"\s+", " ", data.nombre_referente.strip())
    if not name:
        raise HTTPException(status_code=400, detail="El nombre del referente es obligatorio")
    existing = await db.referentes.find_one({"nombre_norm": _norm(name)}, {"_id": 0})
    if existing:
        if not existing.get("estatus"):
            await db.referentes.update_one({"referente_id": existing["referente_id"]}, {"$set": {"estatus": True}})
            existing["estatus"] = True
        return existing
    doc = {
        "referente_id": f"ref_{uuid.uuid4().hex[:12]}",
        "nombre_referente": name,
        "nombre_norm": _norm(name),
        "tipo_referente": data.tipo_referente.value,
        "empresa": (data.empresa or "").strip(),
        "persona": (data.persona or "").strip(),
        "estatus": True,
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email", "") if user else "sistema",
    }
    await db.referentes.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def resolve_contact_referente(user: dict, referente_id: Optional[str], nuevo: Optional[ReferenteIn]) -> Optional[dict]:
    """Devuelve el referente a vincular a un Contacto Inicial (existente o creado en caliente)."""
    if nuevo:
        if not await can_create_referente(user):
            raise HTTPException(status_code=403, detail="No tiene permiso para registrar nuevos referentes")
        return await create_or_get_referente(nuevo, user)
    if referente_id:
        ref = await db.referentes.find_one({"referente_id": referente_id}, {"_id": 0})
        if not ref:
            raise HTTPException(status_code=400, detail="Referente no encontrado")
        return ref
    return None


async def migrate_free_text_referidos():
    """Convierte el texto libre 'referred_by' de Contactos Iniciales en Referentes vinculados (idempotente)."""
    async for c in db.initial_contacts.find(
        {"referred_by": {"$nin": [None, ""]}, "referente_id": {"$in": [None, ""]}},
        {"_id": 0, "contact_id": 1, "referred_by": 1},
    ):
        ref = await create_or_get_referente(ReferenteIn(nombre_referente=c["referred_by"][:150], tipo_referente=TipoReferente.EMPRESA), None)
        await db.initial_contacts.update_one(
            {"contact_id": c["contact_id"]},
            {"$set": {"referente_id": ref["referente_id"], "referred_by": ref["nombre_referente"]}},
        )


@router.get("/referentes")
async def list_referentes(include_inactive: bool = False, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    query = {"merged_into": {"$exists": False}} if include_inactive and _is_admin(user) else {"estatus": True}
    refs = await db.referentes.find(query, {"_id": 0, "nombre_norm": 0}).sort("nombre_referente", 1).to_list(5000)
    counts = {r["_id"]: r["n"] async for r in db.initial_contacts.aggregate([
        {"$match": {"referente_id": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$referente_id", "n": {"$sum": 1}}},
    ])}
    for r in refs:
        r["contactos"] = counts.get(r["referente_id"], 0)
    refs.sort(key=lambda r: r["nombre_referente"].casefold())
    return {"items": refs, "can_create": await can_create_referente(user)}


@router.post("/referentes")
async def create_referente(data: ReferenteIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not await can_create_referente(user):
        raise HTTPException(status_code=403, detail="No tiene permiso para registrar nuevos referentes")
    if await db.referentes.find_one({"nombre_norm": _norm(data.nombre_referente)}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="Ya existe un referente con ese nombre")
    return await create_or_get_referente(data, user)


@router.put("/referentes/{referente_id}")
async def update_referente(referente_id: str, data: ReferenteUpdate, authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    ref = await db.referentes.find_one({"referente_id": referente_id}, {"_id": 0})
    if not ref:
        raise HTTPException(status_code=404, detail="Referente no encontrado")
    updates = {k: (v.value if isinstance(v, Enum) else (v.strip() if isinstance(v, str) else v))
               for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "nombre_referente" in updates:
        clash = await db.referentes.find_one({"nombre_norm": _norm(updates["nombre_referente"]), "referente_id": {"$ne": referente_id}}, {"_id": 1})
        if clash:
            raise HTTPException(status_code=409, detail="Ya existe otro referente con ese nombre")
        updates["nombre_norm"] = _norm(updates["nombre_referente"])
    if not updates:
        return ref
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.referentes.update_one({"referente_id": referente_id}, {"$set": updates})
    if "nombre_referente" in updates:
        await db.initial_contacts.update_many({"referente_id": referente_id}, {"$set": {"referred_by": updates["nombre_referente"]}})
    return await db.referentes.find_one({"referente_id": referente_id}, {"_id": 0, "nombre_norm": 0})


@router.post("/referentes/merge")
async def merge_referentes(data: MergeIn, authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    sources = [s for s in data.source_ids if s != data.target_id]
    target = await db.referentes.find_one({"referente_id": data.target_id}, {"_id": 0})
    if not target or not sources:
        raise HTTPException(status_code=400, detail="Seleccione un referente destino y al menos un duplicado")
    moved = await db.initial_contacts.update_many(
        {"referente_id": {"$in": sources}},
        {"$set": {"referente_id": target["referente_id"], "referred_by": target["nombre_referente"]}},
    )
    merged = await db.referentes.update_many(
        {"referente_id": {"$in": sources}},
        {"$set": {"estatus": False, "merged_into": target["referente_id"], "nombre_norm": None,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "contactos_reasignados": moved.modified_count, "referentes_fusionados": merged.modified_count}


@router.delete("/referentes/{referente_id}")
async def delete_referente(referente_id: str, authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    ref = await db.referentes.find_one({"referente_id": referente_id}, {"_id": 0, "nombre_referente": 1})
    if not ref:
        raise HTTPException(status_code=404, detail="Referente no encontrado")
    linked = await db.initial_contacts.count_documents({"referente_id": referente_id})
    if linked:
        raise HTTPException(status_code=409, detail=f"No se puede eliminar: tiene {linked} contacto(s) inicial(es) vinculado(s). Fusiónelo o inactívelo.")
    await db.referentes.delete_one({"referente_id": referente_id})
    return {"ok": True, "message": f"Referente «{ref['nombre_referente']}» eliminado"}
