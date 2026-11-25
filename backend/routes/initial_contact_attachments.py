"""Adjunto de respaldo (imagen o correo .eml) del Contacto Inicial."""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, File, Header, HTTPException, Response, UploadFile

from config import db, get_current_user
from services.object_storage import APP_NAME, get_object, put_object

router = APIRouter(tags=["initial-contact-attachments"])
MAX_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
FORMAT_ERROR = "Formato no permitido: solo se admiten imágenes (.jpg, .jpeg, .png, .webp) o correos .eml"


async def _read_valid(file: UploadFile) -> tuple[bytes, str, str, str]:
    name = (file.filename or "").strip() or "adjunto"
    ext = os.path.splitext(name)[1].lower()
    ctype = (file.content_type or "").lower()
    if ext in IMAGE_TYPES and ctype in (IMAGE_TYPES[ext], "image/jpg", "application/octet-stream", ""):
        tipo, ctype = "IMAGEN", IMAGE_TYPES[ext]
    elif ext == ".eml" and ctype in ("message/rfc822", "application/octet-stream", "text/plain", ""):
        tipo, ctype = "EML", "message/rfc822"
    else:
        raise HTTPException(400, FORMAT_ERROR)
    data = await file.read()
    if not data:
        raise HTTPException(400, "El archivo está vacío")
    if len(data) > MAX_BYTES:
        raise HTTPException(400, "El archivo supera el tamaño máximo permitido de 10 MB")
    return data, name, tipo, ctype


def _store(contact_id: str, data: bytes, name: str, tipo: str, ctype: str, user: dict) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    ext = os.path.splitext(name)[1].lower()
    path = f"{APP_NAME}/storage/clientes/contacto_inicial/{contact_id}/{ts}_{uuid.uuid4().hex[:12]}{ext}"
    try:
        put_object(path, data, ctype)
    except Exception:
        raise HTTPException(500, "No se pudo almacenar el archivo adjunto")
    return {"adjunto_url": path, "adjunto_nombre_original": name, "adjunto_tipo": tipo,
            "adjunto_content_type": ctype, "adjunto_size": len(data),
            "adjunto_subido_por": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", ""),
            "adjunto_fecha": datetime.now(timezone.utc).isoformat()}


async def consume_staged(staged_id: Optional[str], user: dict) -> Optional[dict]:
    """Recupera (y elimina) un adjunto pre-cargado para incluirlo en el alta del contacto."""
    if not staged_id:
        return None
    rec = await db.initial_contact_staged_attachments.find_one_and_delete({"staged_id": staged_id, "user_id": user["user_id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(400, "El adjunto pre-cargado no existe o expiró; vuelva a adjuntarlo")
    return rec


@router.post("/initial-contacts/attachments/stage")
async def stage_attachment(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    data, name, tipo, ctype = await _read_valid(file)
    contact_id = f"ic_{uuid.uuid4().hex[:12]}"
    rec = {"staged_id": f"stg_{uuid.uuid4().hex[:12]}", "user_id": user["user_id"], "contact_id": contact_id,
           "fields": _store(contact_id, data, name, tipo, ctype, user)}
    await db.initial_contact_staged_attachments.insert_one({**rec})
    return {"staged_id": rec["staged_id"], "adjunto_nombre_original": name, "adjunto_tipo": tipo}


async def _contact(contact_id: str) -> dict:
    c = await db.initial_contacts.find_one({"contact_id": contact_id}, {"_id": 0, "bitacora": 0})
    if not c:
        raise HTTPException(404, "Contacto no encontrado")
    return c


@router.post("/initial-contacts/{contact_id}/attachment")
async def upload_attachment(contact_id: str, file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prev = await _contact(contact_id)
    data, name, tipo, ctype = await _read_valid(file)
    fields = _store(contact_id, data, name, tipo, ctype, user)
    action = "reemplazó" if prev.get("adjunto_url") else "adjuntó"
    await db.initial_contacts.update_one({"contact_id": contact_id}, {
        "$set": {**fields, "updated_at": fields["adjunto_fecha"]},
        "$push": {"bitacora": {"entry_id": f"be_{uuid.uuid4().hex[:8]}", "action": "attachment",
                               "description": f"{fields['adjunto_subido_por']} {action} el documento de respaldo: {name}",
                               "user_id": user["user_id"], "user_name": fields["adjunto_subido_por"], "timestamp": fields["adjunto_fecha"]}}})
    return {k: v for k, v in fields.items() if k != "adjunto_url"} | {"has_attachment": True}


@router.delete("/initial-contacts/{contact_id}/attachment")
async def delete_attachment(contact_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prev = await _contact(contact_id)
    if not prev.get("adjunto_url"):
        raise HTTPException(404, "El contacto no tiene documento adjunto")
    now = datetime.now(timezone.utc).isoformat()
    uname = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    await db.initial_contacts.update_one({"contact_id": contact_id}, {
        "$set": {"adjunto_url": None, "adjunto_nombre_original": None, "adjunto_tipo": None, "adjunto_content_type": None,
                 "adjunto_size": None, "updated_at": now},
        "$push": {"bitacora": {"entry_id": f"be_{uuid.uuid4().hex[:8]}", "action": "attachment",
                               "description": f"{uname} eliminó el documento de respaldo: {prev.get('adjunto_nombre_original')}",
                               "user_id": user["user_id"], "user_name": uname, "timestamp": now}}})
    return {"message": "Documento adjunto eliminado"}


async def _bytes(contact_id: str) -> tuple[dict, bytes]:
    c = await _contact(contact_id)
    if not c.get("adjunto_url"):
        raise HTTPException(404, "El contacto no tiene documento adjunto")
    try:
        data, _ = get_object(c["adjunto_url"])
    except Exception:
        raise HTTPException(500, "No se pudo obtener el archivo adjunto")
    return c, data


@router.get("/initial-contacts/{contact_id}/attachment")
async def download_attachment(contact_id: str, inline: bool = False, authorization: Optional[str] = Header(None)):
    await get_current_user(authorization)
    c, data = await _bytes(contact_id)
    disp = "inline" if inline else "attachment"
    return Response(content=data, media_type=c.get("adjunto_content_type") or "application/octet-stream",
                    headers={"Content-Disposition": f"{disp}; filename*=UTF-8''{quote(c.get('adjunto_nombre_original') or 'adjunto')}"})


@router.get("/initial-contacts/{contact_id}/attachment/email")
async def view_attachment_email(contact_id: str, authorization: Optional[str] = Header(None)):
    from services.eml_parser import eml_summary
    await get_current_user(authorization)
    c, data = await _bytes(contact_id)
    summary = eml_summary(data) if c.get("adjunto_tipo") == "EML" else None
    if summary is None:
        raise HTTPException(400, "El adjunto no es un correo .eml válido")
    return summary


@router.get("/initial-contacts/{contact_id}/attachment/email/attachments/{index}")
async def download_attachment_email_part(contact_id: str, index: int, authorization: Optional[str] = Header(None)):
    from services.eml_parser import eml_attachment
    await get_current_user(authorization)
    _, data = await _bytes(contact_id)
    found = eml_attachment(data, index)
    if not found:
        raise HTTPException(404, "Adjunto no encontrado en el correo")
    filename, ctype, payload = found
    return Response(content=payload, media_type=ctype, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})
