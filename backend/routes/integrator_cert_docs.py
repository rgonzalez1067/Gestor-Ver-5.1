"""Routes: Carpeta digital «Documentos de la Certificación» por Aplicativo (fase 1: estructura en blanco)."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from config import db, get_current_user

router = APIRouter(tags=["integrator-cert-docs"])
STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"


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
