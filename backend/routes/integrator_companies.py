"""Empresas Integradoras (nivel padre) y su relación con los Aplicativos (db.integrators)."""
import os
import re
import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, File, Header, HTTPException, Response, UploadFile
from pydantic import BaseModel

from config import db, get_current_user, require_permission, UPLOADS_DIR
from services.integrator_companies import (
    COLL, EMAIL_RE, clean_name, clean_technicians, is_incomplete, link_orphan_integrators, norm_company, normalize_rif,
)

router = APIRouter()
RIF_DIR = UPLOADS_DIR / "integrator_rif"
RIF_TYPES = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}
APP_FIELDS = {"_id": 0, "integrator_id": 1, "app_name": 1, "integration_type": 1, "integration_modality": 1,
              "integrator_status": 1, "integrator_type": 1, "integration_phase": 1, "componente_version": 1,
              "cert_version": 1, "project_scope": 1, "implementador": 1, "gestor": 1, "empresa_integradora_id": 1}


class CompanyContact(BaseModel):
    contact_id: Optional[str] = None
    full_name: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    role: Optional[str] = ""


class CompanyPayload(BaseModel):
    tipo_persona: Literal["Natural", "Jurídica"]
    razon_social: str
    rif: str
    direccion_fiscal: str
    contacts: List[CompanyContact]


class MovePayload(BaseModel):
    empresa_integradora_id: str


async def _validated(p: CompanyPayload, empresa_id: Optional[str] = None) -> dict:
    razon = clean_name(p.razon_social)
    if not razon:
        raise HTTPException(400, "El Nombre o Razón Social es obligatorio")
    if len(razon) > 200:
        raise HTTPException(400, "El Nombre o Razón Social no puede superar 200 caracteres")
    rif = normalize_rif(p.rif)
    if not rif:
        raise HTTPException(400, "RIF inválido. Formato esperado: J-30112233-4 o V-12345678-9")
    if p.tipo_persona == "Natural" and rif[0] not in "VE":
        raise HTTPException(400, "Para Persona Natural el RIF debe iniciar con V o E")
    if p.tipo_persona == "Jurídica" and rif[0] not in "JGPC":
        raise HTTPException(400, "Para Persona Jurídica el RIF debe iniciar con J, G, P o C")
    if not clean_name(p.direccion_fiscal):
        raise HTTPException(400, "La Dirección Fiscal es obligatoria")
    contacts = []
    for c in p.contacts:
        name = clean_name(c.full_name)
        if not name:
            continue
        email = (c.email or "").strip()
        if email and not EMAIL_RE.match(email):
            raise HTTPException(400, f"Email inválido para el contacto {name}")
        contacts.append({"contact_id": c.contact_id or f"ctc_{uuid.uuid4().hex[:8]}", "full_name": name,
                         "phone": (c.phone or "").strip(), "email": email, "role": (c.role or "").strip()})
    if not contacts:
        raise HTTPException(400, "Debe registrar al menos un contacto corporativo")
    not_self = {"empresa_id": {"$ne": empresa_id}} if empresa_id else {}
    if await db[COLL].find_one({"rif": rif, **not_self}, {"_id": 1}):
        raise HTTPException(409, f"Ya existe una Empresa Integradora con el RIF {rif}")
    if await db[COLL].find_one({"norm_name": norm_company(razon), **not_self}, {"_id": 1}):
        raise HTTPException(409, f"Ya existe una Empresa Integradora llamada «{razon}»")
    return {"tipo_persona": p.tipo_persona, "razon_social": razon, "norm_name": norm_company(razon), "rif": rif,
            "direccion_fiscal": p.direccion_fiscal.strip(), "contacts": contacts}


def _present(e: dict, apps: list) -> dict:
    e.pop("norm_name", None)
    e["ficha_incompleta"] = is_incomplete(e)
    e["apps"] = sorted(apps, key=lambda a: (a.get("app_name") or "").lower())
    e["app_count"] = len(apps)
    first = (e.get("contacts") or [None])[0]
    e["principal_contact"] = (first or {}).get("full_name") or ""
    return e


@router.get("/integrator-companies")
async def list_companies(authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    await link_orphan_integrators()
    apps_by = {}
    async for a in db.integrators.find({}, APP_FIELDS):
        apps_by.setdefault(a.get("empresa_integradora_id"), []).append(a)
    out = [_present(e, apps_by.get(e["empresa_id"], [])) async for e in db[COLL].find({}, {"_id": 0})]
    out.sort(key=lambda e: e["razon_social"].lower())
    return out


@router.get("/integrator-companies/technicians")
async def technician_suggestions(integrator_id: str, authorization: Optional[str] = Header(None)):
    """Técnicos conocidos del aplicativo: directorio del aplicativo + proyectos previos."""
    await get_current_user(authorization)
    seen, out = set(), []

    def add(name, email, phone, role, source):
        name = clean_name(name)
        k = (email or "").strip().lower() or name.lower()
        if name and k not in seen:
            seen.add(k)
            out.append({"name": name, "email": (email or "").strip(), "phone": (phone or "").strip(), "role": role or "", "source": source})

    intg = await db.integrators.find_one({"integrator_id": integrator_id}, {"_id": 0, "contacts": 1})
    for c in (intg or {}).get("contacts") or []:
        add(c.get("name"), c.get("email"), c.get("phone"), c.get("role"), "Aplicativo")
    async for p in db.projects.find({"integrator_id": integrator_id, "integration_technicians.0": {"$exists": True}},
                                    {"_id": 0, "integration_technicians": 1}):
        for t in p.get("integration_technicians") or []:
            add(t.get("name"), t.get("email"), t.get("phone"), t.get("role"), "Proyecto")
    return sorted(out, key=lambda t: t["name"].lower())


@router.get("/integrator-companies/{empresa_id}")
async def get_company(empresa_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    e = await db[COLL].find_one({"empresa_id": empresa_id}, {"_id": 0})
    if not e:
        raise HTTPException(404, "Empresa Integradora no encontrada")
    apps = await db.integrators.find({"empresa_integradora_id": empresa_id}, APP_FIELDS).to_list(None)
    return _present(e, apps)


@router.post("/integrator-companies")
async def create_company(payload: CompanyPayload, authorization: Optional[str] = Header(None)):
    user = await require_permission(authorization, "integradores", "edit")
    data = await _validated(payload)
    now = datetime.now(timezone.utc).isoformat()
    doc = {"empresa_id": f"emp_{uuid.uuid4().hex[:12]}", **data, "rif_document_url": None, "rif_document_filename": None,
           "migrated": False, "created_at": now, "created_by": user.get("email")}
    await db[COLL].insert_one(dict(doc))
    return _present(doc, [])


@router.put("/integrator-companies/{empresa_id}")
async def update_company(empresa_id: str, payload: CompanyPayload, authorization: Optional[str] = Header(None)):
    user = await require_permission(authorization, "integradores", "edit")
    existing = await db[COLL].find_one({"empresa_id": empresa_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Empresa Integradora no encontrada")
    data = await _validated(payload, empresa_id)
    data.update({"updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user.get("email")})
    await db[COLL].update_one({"empresa_id": empresa_id}, {"$set": data})
    if data["razon_social"] != existing.get("razon_social"):
        await db.integrators.update_many({"empresa_integradora_id": empresa_id}, {"$set": {"name": data["razon_social"]}})
    return await get_company(empresa_id, authorization)


@router.delete("/integrator-companies/{empresa_id}")
async def delete_company(empresa_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if user.get("role") != "admin":
        raise HTTPException(403, "Solo un administrador puede eliminar Empresas Integradoras")
    n = await db.integrators.count_documents({"empresa_integradora_id": empresa_id})
    if n:
        raise HTTPException(400, f"No se puede eliminar: la empresa tiene {n} aplicativo(s) asociado(s)")
    res = await db[COLL].delete_one({"empresa_id": empresa_id})
    if not res.deleted_count:
        raise HTTPException(404, "Empresa Integradora no encontrada")
    return {"message": "Empresa Integradora eliminada"}


@router.post("/integrator-companies/{empresa_id}/rif-document")
async def upload_rif_document(empresa_id: str, file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    user = await require_permission(authorization, "integradores", "edit")
    e = await db[COLL].find_one({"empresa_id": empresa_id}, {"_id": 0, "rif": 1})
    if not e:
        raise HTTPException(404, "Empresa Integradora no encontrada")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in RIF_TYPES:
        raise HTTPException(400, "Formato no permitido. Use PDF, JPG o PNG")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "El archivo supera 10 MB")
    fname = f"{empresa_id}_{re.sub(r'[^A-Za-z0-9]', '', e.get('rif') or 'sinrif')}_{uuid.uuid4().hex[:6]}{ext}"
    from services.pdf_storage import save_pdf_dual
    save_pdf_dual(RIF_DIR / fname, content, f"integrator_rif/{fname}")
    upd = {"rif_document_url": f"/uploads/integrator_rif/{fname}", "rif_document_filename": file.filename,
           "rif_updated_at": datetime.now(timezone.utc).isoformat(), "rif_updated_by": user.get("email")}
    await db[COLL].update_one({"empresa_id": empresa_id}, {"$set": upd})
    return upd


@router.get("/integrator-companies/{empresa_id}/rif-document")
async def download_rif_document(empresa_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    e = await db[COLL].find_one({"empresa_id": empresa_id}, {"_id": 0})
    if not e or not e.get("rif_document_url"):
        raise HTTPException(404, "La empresa no tiene un documento RIF archivado")
    rel = e["rif_document_url"].replace("/uploads/", "", 1)
    ctype = RIF_TYPES.get(os.path.splitext(rel)[1].lower(), "application/octet-stream")
    from services.pdf_storage import get_pdf_from_storage
    res = get_pdf_from_storage(rel)
    if res is not None:
        content = res[0]
    else:
        path = UPLOADS_DIR / rel
        if not path.exists():
            raise HTTPException(404, "Archivo RIF no encontrado en el servidor")
        content = path.read_bytes()
    return Response(content=content, media_type=ctype,
                    headers={"Content-Disposition": f'inline; filename="{e.get("rif_document_filename") or os.path.basename(rel)}"'})


@router.put("/integrators/{integrator_id}/company")
async def move_app(integrator_id: str, payload: MovePayload, authorization: Optional[str] = Header(None)):
    user = await require_permission(authorization, "integradores", "edit")
    e = await db[COLL].find_one({"empresa_id": payload.empresa_integradora_id}, {"_id": 0, "razon_social": 1, "empresa_id": 1})
    if not e:
        raise HTTPException(404, "Empresa Integradora no encontrada")
    res = await db.integrators.update_one({"integrator_id": integrator_id},
                                          {"$set": {"empresa_integradora_id": e["empresa_id"], "name": e["razon_social"]}})
    if not res.matched_count:
        raise HTTPException(404, "Aplicativo no encontrado")
    return {"message": f"Aplicativo vinculado a {e['razon_social']}"}


def validate_technicians(techs):
    try:
        return clean_technicians(techs)
    except ValueError as ex:
        raise HTTPException(400, str(ex))
