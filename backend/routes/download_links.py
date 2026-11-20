"""Enlaces de descarga temporales para archivos que no pueden viajar como adjunto (.exe)."""
import os
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote as _q

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, HTMLResponse

from config import db
from services.object_storage import put_object, get_object

router = APIRouter()

LINK_ONLY_EXTS = (".exe",)
LINK_MAX_BYTES = 50 * 1024 * 1024
LINK_TTL_DAYS = 30


def is_link_only(filename: str) -> bool:
    return (filename or "").lower().endswith(LINK_ONLY_EXTS)


async def split_link_only_attachments(project_id: str, atts: list, user_name: str):
    """Separa los .exe: los guarda y devuelve (adjuntos_restantes, html_enlaces, registros)."""
    keep, links = [], []
    for att in atts:
        fname = att.get("filename") or "archivo"
        if not is_link_only(fname):
            keep.append(att)
            continue
        content = att.get("content", b"")
        if len(content) > LINK_MAX_BYTES:
            raise HTTPException(status_code=400, detail=f'"{fname}" supera el máximo de 50 MB para archivos .exe')
        token = uuid.uuid4().hex + uuid.uuid4().hex[:8]
        path = f"{os.environ.get('APP_NAME', 'meganexus')}/download_links/{project_id}/{token}"
        put_object(path, content, "application/octet-stream")
        now = datetime.now(timezone.utc)
        rec = {"token": token, "project_id": project_id, "filename": fname, "size": len(content),
               "storage_path": path, "created_by": user_name, "created_at": now.isoformat(),
               "expires_at": (now + timedelta(days=LINK_TTL_DAYS)).isoformat(), "downloads": 0}
        await db.download_links.insert_one(dict(rec))
        base = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
        rec["url"] = f"{base}/api/public/downloads/{token}"
        links.append(rec)
    if not links:
        return keep, "", []
    exp = datetime.fromisoformat(links[0]["expires_at"]).strftime("%d/%m/%Y")
    items = "".join(
        f'<li style="margin:4px 0;"><a href="{r["url"]}" style="color:#1d4ed8;font-weight:bold;">{r["filename"]}</a>'
        f' <span style="color:#64748b;font-size:12px;">({max(1, r["size"] // 1024)} KB)</span></li>' for r in links)
    html = (f'<div style="margin-top:16px;padding:12px 14px;border:1px solid #cbd5e1;border-radius:8px;background:#f8fafc;font-family:Arial,sans-serif;">'
            f'<p style="margin:0 0 6px;font-weight:bold;color:#0f172a;">Archivos para descargar</p>'
            f'<ul style="margin:0;padding-left:18px;font-size:13px;">{items}</ul>'
            f'<p style="margin:8px 0 0;color:#64748b;font-size:11px;">Enlaces disponibles hasta el {exp}.</p></div>')
    return keep, html, [{k: r[k] for k in ("token", "filename", "size", "url", "expires_at")} for r in links]


@router.get("/public/downloads/{token}")
async def public_download(token: str):
    rec = await db.download_links.find_one({"token": token}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Enlace no válido")
    if datetime.fromisoformat(rec["expires_at"]) < datetime.now(timezone.utc):
        return HTMLResponse("<h3 style='font-family:Arial'>Este enlace de descarga venció. Solicite un nuevo envío.</h3>", status_code=410)
    data, _ = get_object(rec["storage_path"])
    await db.download_links.update_one({"token": token}, {"$inc": {"downloads": 1}})
    return Response(content=data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_q(rec['filename'])}"})
