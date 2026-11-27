"""Respaldo de Archivos (Object Storage): exporta e importa todos los anexos del almacenamiento en la nube.

El Respaldo Total solo contiene la base de datos (con las rutas de los archivos). Este respaldo
complementario empaqueta los archivos reales (expedientes, contacto inicial, comunicaciones, logos,
anexos de proyectos/cotizaciones, PDFs) para restaurarlos en otro servidor con las MISMAS rutas.
"""
import asyncio
import io
import json
import logging
import os
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Form, Header, HTTPException

from config import db
from routes.data_migration import (
    _BACKUP_EXCLUDE, _GridZipWriter, _assemble_upload_to_gridfs_sync, _cleanup_stale_backups,
    _delete_backup_gridfs, _require_admin, _sync_gridfs_bucket,
)
from services.object_storage import APP_NAME, get_object, list_objects, put_object
from services.pdf_storage import APP_ENV

logger = logging.getLogger(__name__)
router = APIRouter()

ROOT_PREFIXES = [f"{APP_NAME}/", f"pdfs/{APP_ENV}/"]  # pdfs/ se separa por ambiente (preview/production)
_CHARSET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-./ "
GROUP_LABEL = "archivos_nube"


def _list_all(prefix: str, out: dict):
    """Lista todo bajo `prefix`. La API devuelve máx. 1000 resultados ORDENADOS y sin paginación:
    si se trunca, se re-consulta (en paralelo) solo con los prefijos posteriores al último recibido."""
    from concurrent.futures import ThreadPoolExecutor
    pending = [prefix]
    with ThreadPoolExecutor(max_workers=16) as ex:
        while pending:
            results = list(ex.map(lambda p: (p, list_objects(p)), pending))
            pending = []
            for p, (objs, truncated) in results:
                for o in objs:
                    out[o["path"]] = o
                if not truncated or not objs:
                    continue
                last = objs[-1]["path"]
                if len(last) <= len(p):
                    continue
                c0 = last[len(p)]
                pending.append(p + c0)
                pending.extend(p + ch for ch in sorted(set(_CHARSET)) if ch > c0)


def _scan_refs(sdb) -> set:
    """Rutas de storage referenciadas en la BD (red de seguridad para nombres con caracteres especiales)."""
    refs = set()

    def walk(v):
        if isinstance(v, str):
            if len(v) < 600 and any(v.startswith(p) for p in ROOT_PREFIXES):
                refs.add(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    for cname in sdb.list_collection_names():
        if cname in _BACKUP_EXCLUDE or cname.startswith("backups") or cname in ("audit_trails", "cron_runs"):
            continue
        for doc in sdb[cname].find({}, {"content_b64": 0, "data": 0}).batch_size(200):
            walk(doc)
    return refs


def _build_files_backup_sync(job_id: str, user: dict, db_name: str):
    from pymongo import MongoClient
    sclient = MongoClient(os.environ["MONGO_URL"])
    sdb = sclient[db_name]
    bucket = _sync_gridfs_bucket(sdb)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"respaldo_archivos_{db_name}_{ts}.zip"
    grid_in = bucket.open_upload_stream(f"{job_id}.zip", metadata={"job_id": job_id, "filename": filename})
    closed = False
    try:
        found = {}
        for p in ROOT_PREFIXES:
            _list_all(p, found)
        for r in _scan_refs(sdb):
            found.setdefault(r, {"path": r})
        paths = sorted(found)
        sdb.backup_jobs.update_one({"job_id": job_id}, {"$set": {"total_collections": len(paths), "phase": "copying"}})
        manifest = {"type": "files-backup", "schema_version": 1, "app_name": APP_NAME, "db_name": db_name,
                    "exported_at": datetime.now(timezone.utc).isoformat(), "exported_by": user.get("email"),
                    "files": [], "missing": []}
        manifest["source_env"] = APP_ENV

        def fetch(path):
            try:
                data, ctype = get_object(path)
                return path, data, ctype, None
            except Exception as e:
                return path, None, None, str(e)[:200]

        from concurrent.futures import ThreadPoolExecutor
        # Archivos ya comprimidos (PDF/imágenes) → ZIP_STORED: rápido y sin costo de CPU
        with zipfile.ZipFile(_GridZipWriter(grid_in), "w", zipfile.ZIP_STORED, allowZip64=True) as zf, ThreadPoolExecutor(8) as ex:
            done = 0
            for start in range(0, len(paths), 16):
                for path, data, ctype, err in ex.map(fetch, paths[start:start + 16]):
                    if err:
                        manifest["missing"].append({"path": path, "error": err})
                    else:
                        zf.writestr(f"files/{path}", data)
                        manifest["files"].append({"path": path, "size": len(data), "content_type": ctype})
                    done += 1
                sdb.backup_jobs.update_one({"job_id": job_id}, {"$set": {"progress_collections": done}})
            manifest["total_files"] = len(manifest["files"])
            manifest["total_bytes"] = sum(f["size"] for f in manifest["files"])
            zf.writestr("files_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        grid_in.close()
        closed = True
        fdoc = sdb["backups.files"].find_one({"_id": grid_in._id}) or {}
        sdb.backup_jobs.update_one({"job_id": job_id}, {"$set": {
            "status": "ready", "gridfs_id": grid_in._id, "filename": filename, "size_bytes": int(fdoc.get("length", 0)),
            "collections": manifest["total_files"], "missing_files": len(manifest["missing"]),
            "ready_at": datetime.now(timezone.utc).isoformat(),
        }})
        sdb.bitacora.insert_one({"action": "files_backup_export", "files": manifest["total_files"],
                                 "missing": len(manifest["missing"]), "executed_by": user.get("email"),
                                 "executed_at": datetime.now(timezone.utc).isoformat()})
    except Exception as e:  # noqa: BLE001
        logger.error(f"[files-backup] job {job_id} falló: {e}")
        try:
            grid_in.abort() if not closed else bucket.delete(grid_in._id)
        except Exception:
            pass
        sdb.backup_jobs.update_one({"job_id": job_id}, {"$set": {"status": "error", "error": str(e)}})
    finally:
        sclient.close()


@router.post("/admin/files-backup/build")
async def files_backup_build(authorization: Optional[str] = Header(None)):
    """Arma en 2º plano el ZIP con todos los archivos. Usa build-status / export-ticket / export del Respaldo Total."""
    user = await _require_admin(authorization)
    await _cleanup_stale_backups()
    async for prev in db.backup_jobs.find({"user_id": user.get("user_id"), "group_label": GROUP_LABEL}):
        await _delete_backup_gridfs(prev.get("gridfs_id"))
        await db.backup_jobs.delete_one({"_id": prev["_id"]})
    job_id = uuid.uuid4().hex
    await db.backup_jobs.insert_one({
        "job_id": job_id, "status": "building", "user_id": user.get("user_id"), "user_email": user.get("email"),
        "group_label": GROUP_LABEL, "kind": "files", "created_at": datetime.now(timezone.utc).isoformat(),
        "progress_collections": 0, "total_collections": 0, "gridfs_id": None, "filename": None, "error": None,
    })
    asyncio.create_task(asyncio.to_thread(_build_files_backup_sync, job_id, {"email": user.get("email")}, db.name))
    return {"job_id": job_id, "status": "building"}


def _restore_files_sync(job_id: str, upload_id: str, db_name: str):
    from bson import ObjectId
    from pymongo import MongoClient
    sclient = MongoClient(os.environ["MONGO_URL"])
    sdb = sclient[db_name]
    jobs = sdb.files_restore_jobs
    try:
        gid = _assemble_upload_to_gridfs_sync(upload_id, db_name)
        stream = _sync_gridfs_bucket(sdb).open_download_stream(ObjectId(gid))
        try:
            zf = zipfile.ZipFile(stream)
        except zipfile.BadZipFile:
            raise RuntimeError("El archivo subido no es un ZIP válido o llegó incompleto")
        if "files_manifest.json" not in zf.namelist():
            raise RuntimeError("El ZIP no es un Respaldo de Archivos (falta files_manifest.json)")
        manifest = json.loads(zf.read("files_manifest.json"))
        ctypes = {f["path"]: f.get("content_type") for f in manifest.get("files", [])}
        src_pdfs = f"pdfs/{manifest.get('source_env') or APP_ENV}/"
        entries = [n for n in zf.namelist() if n.startswith("files/") and not n.endswith("/")]
        jobs.update_one({"job_id": job_id}, {"$set": {"total": len(entries), "exported_at": manifest.get("exported_at")}})
        ok, errors = 0, []
        for i, name in enumerate(entries, 1):
            path = name[len("files/"):]
            target = f"pdfs/{APP_ENV}/" + path[len(src_pdfs):] if path.startswith(src_pdfs) else path  # re-mapear ambiente
            try:
                put_object(target, zf.read(name), ctypes.get(path) or "application/octet-stream")
                ok += 1
            except Exception as e:
                errors.append({"path": path, "error": str(e)[:200]})
            if i % 20 == 0 or i == len(entries):
                jobs.update_one({"job_id": job_id}, {"$set": {"done": i, "restored": ok}})
        jobs.update_one({"job_id": job_id}, {"$set": {"status": "done", "restored": ok, "errors": errors[:50],
                                                       "error_count": len(errors), "finished_at": datetime.now(timezone.utc).isoformat()}})
        try:
            _sync_gridfs_bucket(sdb).delete(ObjectId(gid))
        except Exception:
            pass
    except Exception as e:  # noqa: BLE001
        logger.error(f"[files-restore] job {job_id} falló: {e}")
        jobs.update_one({"job_id": job_id}, {"$set": {"status": "error", "error": str(getattr(e, "detail", e))}})
    finally:
        sclient.close()


@router.post("/admin/files-backup/restore")
async def files_backup_restore(upload_id: str = Form(...), authorization: Optional[str] = Header(None)):
    """Restaura al almacenamiento en la nube los archivos de un ZIP ya subido por chunks (upload-init/upload-chunk)."""
    user = await _require_admin(authorization)
    job_id = uuid.uuid4().hex
    await db.files_restore_jobs.insert_one({"job_id": job_id, "status": "running", "done": 0, "total": 0, "restored": 0,
                                            "user_email": user.get("email"), "created_at": datetime.now(timezone.utc).isoformat()})
    asyncio.create_task(asyncio.to_thread(_restore_files_sync, job_id, upload_id, db.name))
    return {"job_id": job_id}


@router.get("/admin/files-backup/restore-status")
async def files_backup_restore_status(job_id: str, authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    job = await db.files_restore_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Restauración no encontrada")
    return job
