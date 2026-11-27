"""Respaldo Programado: Lun/Mié/Vie 8:00pm (Caracas) vía cron de plataforma.

Cada ejecución genera 3 paquetes: Respaldo Total (BD), Maestras (Clientes, Bancos, Inventario...)
y Respaldo de Archivos (nube). Se conservan las últimas KEEP_RUNS ejecuciones y se avisa por correo
a los administradores activos.
"""
import asyncio
import hmac
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from config import db
from routes.data_migration import _MASTER_EXCLUDE, _build_full_backup_sync, _delete_backup_gridfs, _require_admin
from routes.files_backup import _build_files_backup_sync

logger = logging.getLogger(__name__)
router = APIRouter()
KEEP_RUNS = 2
PARTS = [("total", "Respaldo Total (Base de Datos)"), ("maestras", "Maestras (Clientes, Bancos, Inventario...)"),
         ("archivos", "Respaldo de Archivos (nube)")]


async def _new_job(run_id: str, part: str) -> str:
    job_id = uuid.uuid4().hex
    await db.backup_jobs.insert_one({
        "job_id": job_id, "status": "building", "user_id": "scheduled", "user_email": "Respaldo programado",
        "group_label": None if part == "total" else ("maestras" if part == "maestras" else "archivos_nube"),
        "scheduled": True, "run_id": run_id, "part": part, "created_at": datetime.now(timezone.utc).isoformat(),
        "progress_collections": 0, "total_collections": 0, "gridfs_id": None, "filename": None, "error": None,
    })
    return job_id


async def _prune_old_runs():
    runs = await db.scheduled_backup_runs.find({}, {"_id": 0, "run_id": 1}).sort("started_at", -1).to_list(100)
    for r in runs[KEEP_RUNS:]:
        async for j in db.backup_jobs.find({"run_id": r["run_id"], "scheduled": True}):
            await _delete_backup_gridfs(j.get("gridfs_id"))
            await db.backup_jobs.delete_one({"_id": j["_id"]})
        await db.scheduled_backup_runs.update_one({"run_id": r["run_id"]}, {"$set": {"expired": True}})


async def _notify_admins(run: dict):
    from services.email_service import send_email
    admins = await db.users.find({"role": "admin", "is_active": True}, {"_id": 0, "email": 1}).to_list(50)
    to = sorted({a["email"].lower() for a in admins if a.get("email")})
    if not to:
        return
    ok = run["status"] == "ok"
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;'>{p['label']}</td><td><strong style='color:{'#047857' if p['status'] == 'ready' else '#b91c1c'};'>"
        f"{'Listo' if p['status'] == 'ready' else 'Error'}</strong></td><td style='padding-left:12px;'>{round((p.get('size_bytes') or 0) / 1048576, 1)} MB</td></tr>"
        for p in run["parts"])
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"<p><a href='{base}/settings/backup-center'>Ir al Centro de Respaldos</a></p>" if base else ""
    html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#003366;padding:16px;border-radius:8px 8px 0 0;color:white;font-size:18px;">Respaldo Programado {'listo' if ok else 'con errores'}</div>
      <div style="border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 8px 8px;font-size:14px;color:#334155;">
        <p>El respaldo automático del {run['fecha_local']} {'se generó correctamente' if ok else 'terminó con errores'}.</p>
        <table style="font-size:13px;">{rows}</table>
        <p style="margin-top:14px;">Descárgalo desde <strong>Configuración → Centro de Respaldos → Respaldos Programados</strong>.
        Se conservan las últimas {KEEP_RUNS} ejecuciones.</p>{link}
      </div></div>"""
    try:
        await send_email(to=to, subject=f"Respaldo Programado {'listo' if ok else 'con errores'} - {run['fecha_local']}",
                         html=html, action="scheduled_backup")
    except Exception as e:
        logger.error(f"[scheduled-backup] no se pudo notificar: {e}")


async def run_scheduled_backup(run_id: str):
    from zoneinfo import ZoneInfo
    now_local = datetime.now(ZoneInfo("America/Caracas"))
    run = {"run_id": run_id, "status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
           "fecha_local": now_local.strftime("%d/%m/%Y %I:%M %p"), "parts": []}
    await db.scheduled_backup_runs.update_one({"run_id": run_id}, {"$set": run}, upsert=True)
    sys_user = {"email": "respaldo.programado@sistema", "first_name": "Respaldo", "last_name": "Programado"}
    for part, label in PARTS:
        job_id = await _new_job(run_id, part)
        try:
            if part == "total":
                await asyncio.to_thread(_build_full_backup_sync, job_id, sys_user, db.name, None, None)
            elif part == "maestras":
                await asyncio.to_thread(_build_full_backup_sync, job_id, sys_user, db.name, sorted(_MASTER_EXCLUDE), "maestras")
            else:
                await asyncio.to_thread(_build_files_backup_sync, job_id, sys_user, db.name)
        except Exception as e:  # noqa: BLE001
            await db.backup_jobs.update_one({"job_id": job_id}, {"$set": {"status": "error", "error": str(e)}})
        j = await db.backup_jobs.find_one({"job_id": job_id}, {"_id": 0}) or {}
        run["parts"].append({"part": part, "label": label, "job_id": job_id, "status": j.get("status"),
                             "size_bytes": j.get("size_bytes"), "filename": j.get("filename"), "error": j.get("error")})
        await db.scheduled_backup_runs.update_one({"run_id": run_id}, {"$set": {"parts": run["parts"]}})
    run["status"] = "ok" if all(p["status"] == "ready" for p in run["parts"]) else "error"
    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    await db.scheduled_backup_runs.update_one({"run_id": run_id}, {"$set": {"status": run["status"], "finished_at": run["finished_at"]}})
    await _prune_old_runs()
    await _notify_admins(run)
    logger.info(f"[scheduled-backup] {run_id} → {run['status']}")


async def _running():
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    return await db.scheduled_backup_runs.find_one({"status": "running", "started_at": {"$gt": cutoff}})


@router.post("/cron/scheduled-backup")
async def cron_scheduled_backup(request: Request, background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ["WEBHOOK_CRON_SECRET"]
    token = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not token or not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid body")
    run_id = request.headers.get("X-Webhook-Id") or (body or {}).get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="Missing run_id")
    res = await db.cron_runs.update_one({"run_id": run_id}, {"$setOnInsert": {"run_id": run_id, "job": "scheduled-backup", "status": "queued"}}, upsert=True)
    if res.upserted_id is None:
        return {"status": "duplicate"}
    if await _running():
        return {"status": "skipped", "detail": "Ya hay un respaldo programado en curso"}
    background_tasks.add_task(run_scheduled_backup, run_id)
    return {"status": "accepted"}


@router.get("/admin/scheduled-backups")
async def list_scheduled_backups(authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    runs = await db.scheduled_backup_runs.find({"expired": {"$ne": True}}, {"_id": 0}).sort("started_at", -1).to_list(KEEP_RUNS + 2)
    return {"runs": runs, "schedule": "Lunes, Miércoles y Viernes 8:00 PM (hora de Caracas)", "keep_runs": KEEP_RUNS}


@router.post("/admin/scheduled-backups/run-now")
async def run_scheduled_backup_now(background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    if await _running():
        raise HTTPException(409, "Ya hay un respaldo programado en curso")
    run_id = f"manual_{uuid.uuid4().hex[:10]}"
    background_tasks.add_task(run_scheduled_backup, run_id)
    return {"run_id": run_id}
