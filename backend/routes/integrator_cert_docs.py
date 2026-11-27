"""Routes: «Documentos de la Certificación» por Aplicativo + Expediente Digital por Certificado (1:1)."""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, File, Header, HTTPException, Query, Response, UploadFile

from config import db, get_current_user
from services.object_storage import APP_NAME, get_object, put_object

router = APIRouter(tags=["integrator-cert-docs"])
STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"
MAX_BYTES = 25 * 1024 * 1024
EXP_TYPES = {
    ".pdf": "application/pdf", ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
    ".eml": "message/rfc822", ".zip": "application/zip",
}


def folder_path(empresa_id: str, app_id: str) -> str:
    return f"/storage/integradores/{empresa_id or 'sin_empresa'}/aplicativos/{app_id}/documentos_certificacion/"


@router.get("/integrators/{integrator_id}/certification-documents")
async def get_certification_documents(integrator_id: str, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    app = await db.integrators.find_one({"integrator_id": integrator_id}, {"_id": 0, "integrator_id": 1, "empresa_integradora_id": 1})
    if not app:
        raise HTTPException(404, "Aplicativo no encontrado")
    path = folder_path(app.get("empresa_integradora_id"), integrator_id)
    (STORAGE_ROOT / path.removeprefix("/storage/")).mkdir(parents=True, exist_ok=True)
    folder = await db.integrator_cert_folders.find_one({"integrator_id": integrator_id}, {"_id": 0})
    if not folder:
        folder = {"integrator_id": integrator_id, "empresa_id": app.get("empresa_integradora_id"), "path": path,
                  "created_at": datetime.now(timezone.utc).isoformat()}
        await db.integrator_cert_folders.insert_one({**folder})
    docs = await db.integrator_cert_documents.find({"integrator_id": integrator_id}, {"_id": 0}).to_list(500)
    return {"folder": folder, "documents": docs}


# ==================== EXPEDIENTE DIGITAL POR CERTIFICADO ====================

def _uname(user: Optional[dict]) -> str:
    if not user:
        return "Sistema"
    return f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", "")


async def _audit_read(accion: str, doc: dict, user: dict):
    """Registra consultas/descargas (las escrituras ya las audita el interceptor)."""
    await getattr(db, "raw", db)["audit_trails"].insert_one({
        "modulo": "Integradores", "entidad": "certificado_expediente_documentos",
        "registro_id": doc.get("documento_id") or doc.get("certificado_id"), "entidad_id": doc.get("certificado_id"),
        "accion": accion, "valores_anteriores": None,
        "valores_nuevos": {"nombre_documento": doc.get("nombre_documento"), "certificado_id": doc.get("certificado_id")},
        "campos_modificados": None, "usuario_id": user.get("user_id"), "usuario_nombre": _uname(user),
        "usuario_email": user.get("email", ""), "endpoint": "expediente_certificacion",
        "fecha_hora": datetime.now(timezone.utc),
    })


async def store_expediente_doc(certificado_id: str, aplicativo_id: str, filename: str, content: bytes,
                               origen: str, user: Optional[dict], content_type: Optional[str] = None,
                               proyecto_id: Optional[str] = None) -> dict:
    """Guarda un documento en el expediente del certificado (Object Storage + metadatos)."""
    app = await db.integrators.find_one({"integrator_id": aplicativo_id}, {"_id": 0, "empresa_integradora_id": 1}) or {}
    name = os.path.basename(filename or "documento") or "documento"
    ext = os.path.splitext(name)[1].lower()
    ctype = content_type or EXP_TYPES.get(ext, "application/octet-stream")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    path = (f"{APP_NAME}/storage/integradores/{app.get('empresa_integradora_id') or 'sin_empresa'}/aplicativos/{aplicativo_id}"
            f"/certificados/{certificado_id}/expediente/{ts}_{uuid.uuid4().hex[:8]}_{name}")
    put_object(path, content, ctype)
    doc = {
        "documento_id": f"expdoc_{uuid.uuid4().hex[:12]}", "certificado_id": certificado_id,
        "aplicativo_id": aplicativo_id, "proyecto_id": proyecto_id, "nombre_documento": name,
        "ruta_archivo": path, "tipo_mime": ctype, "tamano": len(content), "origen_carga": origen,
        "usuario_carga_id": (user or {}).get("user_id", "sistema"), "usuario_carga_nombre": _uname(user),
        "fecha_carga": datetime.now(timezone.utc).isoformat(),
    }
    await db.certificado_expediente_documentos.insert_one({**doc})
    return doc


async def expediente_counts(cert_ids: list) -> dict:
    rows = await db.certificado_expediente_documentos.aggregate([
        {"$match": {"certificado_id": {"$in": cert_ids}}}, {"$group": {"_id": "$certificado_id", "n": {"$sum": 1}}}]).to_list(1000)
    return {r["_id"]: r["n"] for r in rows}


async def _cert(certificate_id: str) -> dict:
    c = await db.integrator_certificates.find_one({"certificate_id": certificate_id}, {"_id": 0, "content_b64": 0})
    if not c:
        raise HTTPException(404, "Certificado no encontrado")
    return c


@router.get("/integrators/certificates/{certificate_id}/expediente")
async def list_expediente(certificate_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    c = await _cert(certificate_id)
    app = await db.integrators.find_one({"integrator_id": c["integrator_id"]}, {"_id": 0, "app_name": 1, "name": 1}) or {}
    docs = await db.certificado_expediente_documentos.find({"certificado_id": certificate_id}, {"_id": 0}).sort("fecha_carga", 1).to_list(500)
    await _audit_read("CONSULTA", {"certificado_id": certificate_id, "nombre_documento": "Expediente"}, user)
    return {"certificate": {k: c.get(k) for k in ("certificate_id", "created_at", "products_included", "status", "original_name")},
            "aplicativo": app.get("app_name") or app.get("name", ""), "documents": docs}


@router.post("/integrators/certificates/{certificate_id}/expediente")
async def upload_expediente(certificate_id: str, files: List[UploadFile] = File(...), authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    c = await _cert(certificate_id)
    payloads = []
    for f in files:
        name = (f.filename or "").strip()
        ext = os.path.splitext(name)[1].lower()
        if ext not in EXP_TYPES:
            raise HTTPException(400, f"Formato no permitido ({name}). Se admiten: {', '.join(sorted(EXP_TYPES))}")
        data = await f.read()
        if not data:
            raise HTTPException(400, f"El archivo {name} está vacío")
        if len(data) > MAX_BYTES:
            raise HTTPException(400, f"El archivo {name} supera el máximo de 25 MB")
        payloads.append((name, data))
    saved = [await store_expediente_doc(certificate_id, c["integrator_id"], n, d, "MANUAL_POSTERIOR", user) for n, d in payloads]
    return {"uploaded": len(saved), "documents": saved}


@router.get("/integrators/expediente/{documento_id}/download")
async def download_expediente_doc(documento_id: str, inline: bool = False, token: Optional[str] = Query(None),
                                  authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization or (f"Bearer {token}" if token else None))
    doc = await db.certificado_expediente_documentos.find_one({"documento_id": documento_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    try:
        data, _ = get_object(doc["ruta_archivo"])
    except Exception:
        raise HTTPException(500, "No se pudo obtener el archivo del almacenamiento")
    await _audit_read("VISUALIZACION" if inline else "DESCARGA", doc, user)
    disp = "inline" if inline else "attachment"
    return Response(content=data, media_type=doc.get("tipo_mime") or "application/octet-stream",
                    headers={"Content-Disposition": f"{disp}; filename*=UTF-8''{quote(doc['nombre_documento'])}"})
