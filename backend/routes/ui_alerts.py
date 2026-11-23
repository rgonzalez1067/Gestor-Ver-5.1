"""Routes: /api/settings/ui-alerts — encendido/apagado de avisos en pantalla por niveles (todos, departamento, persona)."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from config import db, get_current_user

router = APIRouter(tags=["settings"])
DOC_ID = "ui_alerts"
RESOURCES = ("push", "unread_banner")


class ResourceRule(BaseModel):
    enabled: bool = True
    disabled_departments: List[str] = []
    disabled_users: List[str] = []


class UiAlertsConfig(BaseModel):
    push: ResourceRule = ResourceRule()
    unread_banner: ResourceRule = ResourceRule()


def _is_admin(user: dict) -> bool:
    return user.get("role") == "admin" or bool(user.get("is_admin"))


async def _load() -> UiAlertsConfig:
    doc = await db.app_settings.find_one({"key": DOC_ID}, {"_id": 0}) or {}
    return UiAlertsConfig(**{k: doc[k] for k in RESOURCES if k in doc})


@router.get("/settings/ui-alerts")
async def get_ui_alerts(authorization: Optional[str] = Header(None)):
    if not _is_admin(await get_current_user(authorization)):
        raise HTTPException(status_code=403, detail="Solo administradores")
    users = await db.users.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "user_id": 1, "first_name": 1, "last_name": 1, "email": 1, "departamento": 1},
    ).sort("first_name", 1).to_list(2000)
    departments = sorted({u.get("departamento") for u in users if u.get("departamento")})
    for u in users:
        u["full_name"] = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("email", "")
    return {"config": (await _load()).model_dump(), "departments": departments, "users": users}


@router.put("/settings/ui-alerts")
async def put_ui_alerts(payload: UiAlertsConfig, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Solo administradores")
    await db.app_settings.update_one(
        {"key": DOC_ID},
        {"$set": {**payload.model_dump(), "key": DOC_ID, "updated_at": datetime.now(timezone.utc).isoformat(),
                  "updated_by": user.get("email", "")}},
        upsert=True,
    )
    return {"ok": True}


@router.get("/notifications/ui-alerts/me")
async def my_ui_alerts(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    cfg = await _load()
    dept = user.get("departamento") or ""
    out = {}
    for k in RESOURCES:
        r: ResourceRule = getattr(cfg, k)
        out[k] = r.enabled and dept not in r.disabled_departments and user.get("user_id") not in r.disabled_users
    return out
