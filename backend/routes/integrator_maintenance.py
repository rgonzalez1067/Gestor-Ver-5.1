"""Mantenimiento del Directorio: eliminación segura de empresas vacías / aplicativos y carga de certificados históricos."""
import io
import re
import zipfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from config import db, get_current_user
from services.integrator_companies import COLL, norm_company
from services.integrator_locks import has_flag, CERT_SPECIAL

router = APIRouter()
DELETE_SPECIAL = "integradores:eliminar_registros"


async def _require(authorization, flag, label):
    user = await get_current_user(authorization)
    if not has_flag(user, flag):
        raise HTTPException(403, f"Requiere la Función Especial '{label}'")
    return user


async def _references(intg: dict) -> dict:
    iid = intg["integrator_id"]
    quotes = [{"quote_id": q["quote_id"], "quote_number": q.get("quote_number"), "client_name": q.get("client_name"),
               "status": q.get("status") or q.get("quote_status") or ""}
              async for q in db.quotes.find({"integrator_id": iid}, {"_id": 0, "quote_id": 1, "quote_number": 1, "client_name": 1, "status": 1, "quote_status": 1})]
    pflt = {"integrator_id": iid}
    twins = await db.integrators.count_documents({"name": intg.get("name"), "app_name": intg.get("app_name"), "integrator_id": {"$ne": iid}})
    if not twins:
        # Proyectos antiguos sin integrator_id se ligan por nombre: bloquean solo si es el último registro con ese nombre.
        pflt = {"$or": [{"integrator_id": iid}, {"integrator_id": {"$in": [None, ""]}, "integrator_name": intg.get("name"),
                                                  "integrator_app_name": intg.get("app_name")}]}
    projects = [{"project_id": p["project_id"], "project_number": p.get("project_number"), "client_name": p.get("client_name"), "status": p.get("status")}
                async for p in db.projects.find(pflt, {"_id": 0, "project_id": 1, "project_number": 1, "client_name": 1, "status": 1})]
    certs = await db.integrator_certificates.count_documents({"integrator_id": iid, "status": {"$ne": "anulado"}})
    return {"quotes": quotes, "projects": projects, "certificates": certs}


@router.get("/integrators/{integrator_id}/references")
async def integrator_references(integrator_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    intg = await db.integrators.find_one({"integrator_id": integrator_id}, {"_id": 0})
    if not intg:
        raise HTTPException(404, "Aplicativo no encontrado")
    return await _references(intg)


@router.delete("/integrators/{integrator_id}/safe")
async def delete_app_safe(integrator_id: str, authorization: Optional[str] = Header(None)):
    await _require(authorization, DELETE_SPECIAL, "Eliminar Empresas y Aplicativos")
    intg = await db.integrators.find_one({"integrator_id": integrator_id}, {"_id": 0})
    if not intg:
        raise HTTPException(404, "Aplicativo no encontrado")
    refs = await _references(intg)
    if refs["quotes"] or refs["projects"] or refs["certificates"]:
        raise HTTPException(409, {"message": "No se puede eliminar: el aplicativo está referido. Actualice primero estos registros.", **refs})
    await db.integrators.delete_one({"integrator_id": integrator_id})
    return {"message": f"Aplicativo «{intg.get('app_name') or intg.get('name')}» eliminado"}


@router.delete("/integrator-companies/{empresa_id}/safe")
async def delete_company_safe(empresa_id: str, authorization: Optional[str] = Header(None)):
    await _require(authorization, DELETE_SPECIAL, "Eliminar Empresas y Aplicativos")
    n = await db.integrators.count_documents({"empresa_integradora_id": empresa_id})
    if n:
        raise HTTPException(400, f"No se puede eliminar: la empresa tiene {n} aplicativo(s) asociado(s)")
    res = await db[COLL].delete_one({"empresa_id": empresa_id})
    if not res.deleted_count:
        raise HTTPException(404, "Empresa Integradora no encontrada")
    return {"message": "Empresa Integradora eliminada"}


@router.post("/integrator-companies/purge-empty")
async def purge_empty_companies(authorization: Optional[str] = Header(None)):
    await _require(authorization, DELETE_SPECIAL, "Eliminar Empresas y Aplicativos")
    used = set(await db.integrators.distinct("empresa_integradora_id"))
    ids = [e["empresa_id"] async for e in db[COLL].find({}, {"_id": 0, "empresa_id": 1}) if e["empresa_id"] not in used]
    if ids:
        await db[COLL].delete_many({"empresa_id": {"$in": ids}})
    return {"deleted": len(ids)}


@router.post("/integrators/certificates/rebuild-legacy")
async def rebuild_legacy_certificates(authorization: Optional[str] = Header(None)):
    """Reconstruye el PDF de los aplicativos certificados en el sistema que no tienen certificado en el histórico."""
    user = await _require(authorization, CERT_SPECIAL, "Gestionar Certificados (Gerente de Implementación)")
    from routes.integrators import _resolve_implementer_cert_template, _generate_integration_certificate_pdf, _store_integrator_certificate
    with_cert = set(await db.integrator_certificates.distinct("integrator_id"))
    created, skipped = [], []
    async for intg in db.integrators.find({"certified_at": {"$nin": [None, ""]}, "cert_component": {"$nin": [None, ""]}}, {"_id": 0}):
        label = {"integrator_id": intg["integrator_id"], "name": intg.get("name"), "app_name": intg.get("app_name")}
        if intg["integrator_id"] in with_cert:
            continue
        try:
            tpl = await _resolve_implementer_cert_template(intg)
            pdf = await _generate_integration_certificate_pdf(intg, intg["cert_component"], intg.get("cert_version") or "",
                                                              intg.get("cert_products") or "", base_pdf_bytes=tpl)
            if not pdf:
                raise HTTPException(422, "No se pudo generar el PDF")
        except HTTPException as ex:
            skipped.append({**label, "reason": str(ex.detail).replace("antes de cerrar el proyecto", "y vuelva a reconstruir")})
            continue
        fecha = str(intg["certified_at"])[:10]
        cid = await _store_integrator_certificate(intg["integrator_id"], f"Certificado_{intg.get('name', '')}_{fecha}.pdf", pdf,
                                                  "legacy", f"Reconstruido - certificación del {fecha}", user)
        await db.integrator_certificates.update_one({"certificate_id": cid}, {"$set": {"created_at": intg["certified_at"], "status": "vigente",
                                                                                    "rebuilt_at": datetime.now(timezone.utc).isoformat()}})
        created.append(label)
    return {"created": len(created), "items": created, "skipped": skipped}


def _tokens(s):
    return {t for t in norm_company(s).split() if len(t) > 1}


@router.post("/integrators/certificates/bulk-upload")
async def bulk_upload_certificates(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    """ZIP de PDFs: cada archivo se asocia al aplicativo cuyo nombre (empresa + aplicativo) mejor coincide con el nombre del archivo."""
    user = await _require(authorization, CERT_SPECIAL, "Gestionar Certificados (Gerente de Implementación)")
    from routes.integrators import _store_integrator_certificate
    content = await file.read()
    try:
        z = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(400, "El archivo debe ser un ZIP con certificados PDF")
    apps = [a async for a in db.integrators.find({}, {"_id": 0, "integrator_id": 1, "name": 1, "app_name": 1})]
    for a in apps:
        a["_tok"] = _tokens(f"{a.get('name', '')} {a.get('app_name', '')}")
        a["_name_tok"] = _tokens(a.get("name"))
    matched, unmatched = [], []
    uname = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", "")
    for info in z.infolist():
        fname = info.filename.rsplit("/", 1)[-1]
        if info.is_dir() or not fname or fname.startswith(".") or not fname.lower().endswith(".pdf"):
            continue
        data = z.read(info)
        if not data.startswith(b"%PDF"):
            unmatched.append({"filename": fname, "reason": "No es un PDF válido"})
            continue
        ftok = _tokens(re.sub(r"(?i)certificado|certificacion|\.pdf$", " ", fname))
        scored = []
        for a in apps:
            if not a["_name_tok"] or not a["_name_tok"] <= ftok:
                continue
            scored.append((len(a["_tok"] & ftok) / max(len(a["_tok"]), 1), a))
        scored.sort(key=lambda x: -x[0])
        top = [x for x in scored if scored and x[0] == scored[0][0]]
        if len(top) > 1 and len({(norm_company(t[1].get("name")), norm_company(t[1].get("app_name"))) for t in top}) == 1:
            # Duplicados exactos (mismo nombre y aplicativo): se usa el que tiene más uso (certificación / cotizaciones).
            async def _weight(a):
                full = await db.integrators.find_one({"integrator_id": a["integrator_id"]}, {"_id": 0, "certified_at": 1})
                return (1 if (full or {}).get("certified_at") else 0) + await db.quotes.count_documents({"integrator_id": a["integrator_id"]})
            weights = [await _weight(t[1]) for t in top]
            scored = [top[weights.index(max(weights))]]
        if not scored or (len(scored) > 1 and scored[0][0] == scored[1][0]):
            reason = "Sin coincidencia" if not scored else f"Ambiguo entre {len([s for s in scored if s[0] == scored[0][0]])} aplicativos"
            unmatched.append({"filename": fname, "reason": reason})
            continue
        a = scored[0][1]
        if await db.integrator_certificates.find_one({"integrator_id": a["integrator_id"], "original_name": fname, "size": len(data)}, {"_id": 1}):
            unmatched.append({"filename": fname, "reason": f"Ya estaba cargado en {a.get('name')} · {a.get('app_name')}"})
            continue
        await db.integrator_certificates.update_many(
            {"integrator_id": a["integrator_id"], "status": {"$nin": ["anulado", "reemplazado"]}},
            {"$set": {"status": "reemplazado", "status_updated_at": datetime.now(timezone.utc).isoformat()}})
        cid = await _store_integrator_certificate(a["integrator_id"], fname, data, "manual", f"Carga en lote - {uname}", user)
        await db.integrator_certificates.update_one({"certificate_id": cid}, {"$set": {"status": "vigente"}})
        matched.append({"filename": fname, "integrator_id": a["integrator_id"], "name": a.get("name"), "app_name": a.get("app_name")})
    return {"matched": matched, "unmatched": unmatched}
