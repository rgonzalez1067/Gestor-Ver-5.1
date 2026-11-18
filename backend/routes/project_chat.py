"""Chat interno colaborativo por Proyecto (ACL: Generador, Gerente del Generador, Implementador,
Coordinador de Implementación, Gerente de Implementación; administradores ajenos: solo lectura)."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from config import db, get_current_user

router = APIRouter()

ROLE_GEN, ROLE_GEN_MGR = "Generador", "Gerente Comercial"
ROLE_IMPL, ROLE_COORD, ROLE_IMPL_MGR = "Implementador", "Coordinador de Implementación", "Gerente de Implementación"


class ChatMessageIn(BaseModel):
    text: str


def _uname(u: dict) -> str:
    return f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("name") or u.get("email", "")


_UMAP_CACHE = {"at": 0.0, "map": None}


async def _users_map() -> dict:
    """Usuarios activos (cache en memoria 60s para no consultarlos en cada revisión)."""
    import time
    if _UMAP_CACHE["map"] is not None and time.monotonic() - _UMAP_CACHE["at"] < 60:
        return _UMAP_CACHE["map"]
    users = await db.users.find({"is_active": {"$ne": False}},
                                {"_id": 0, "user_id": 1, "first_name": 1, "last_name": 1, "name": 1, "email": 1,
                                 "supervisor_id": 1, "cargo": 1, "departamento": 1, "role": 1}).to_list(None)
    import time
    _UMAP_CACHE.update(at=time.monotonic(), map={u["user_id"]: u for u in users})
    return _UMAP_CACHE["map"]


def _impl_managers(umap: dict) -> list:
    return [uid for uid, u in umap.items() if u.get("cargo") == "Gerente" and u.get("departamento") == "Implementación"]


def participants(project: dict, umap: dict, impl_mgrs: list) -> dict:
    """user_id → [roles] según la ficha de usuario (supervisores)."""
    out: dict = {}

    def add(uid, role):
        if uid and uid in umap:
            out.setdefault(uid, [])
            if role not in out[uid]:
                out[uid].append(role)

    gen = project.get("created_by_user_id")
    add(gen, ROLE_GEN)
    add((umap.get(gen) or {}).get("supervisor_id"), ROLE_GEN_MGR)
    impl = project.get("assigned_to_user_id")
    add(impl, ROLE_IMPL)
    coord = (umap.get(impl) or {}).get("supervisor_id")
    add(coord, ROLE_COORD)
    mgr = (umap.get(coord) or {}).get("supervisor_id") if coord else None
    for uid in ([mgr] if mgr and mgr in umap else impl_mgrs):
        add(uid, ROLE_IMPL_MGR)
    return out


async def _access(project_id: str, user: dict):
    project = await db.projects.find_one({"project_id": project_id},
                                         {"_id": 0, "project_id": 1, "project_number": 1, "client_name": 1,
                                          "created_by_user_id": 1, "assigned_to_user_id": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    umap = await _users_map()
    parts = participants(project, umap, _impl_managers(umap))
    me = user.get("user_id")
    if me in parts:
        return project, umap, parts, True
    if user.get("role") == "admin":
        return project, umap, parts, False
    raise HTTPException(status_code=403, detail="No participas en el chat de este proyecto")


@router.get("/projects/{project_id}/chat")
async def get_chat(project_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    project, umap, parts, can_write = await _access(project_id, user)
    msgs = await db.project_chat_messages.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(2000)
    reads = {r["user_id"]: r.get("last_read_at", "") for r in await db.project_chat_reads.find(
        {"project_id": project_id}, {"_id": 0}).to_list(None)}
    for m in msgs:
        m["read_by"] = [_uname(umap[uid]) for uid, at in reads.items()
                        if uid != m["user_id"] and uid in parts and uid in umap and at >= m["created_at"]]
    if can_write:
        await db.project_chat_reads.update_one({"project_id": project_id, "user_id": user["user_id"]},
                                               {"$set": {"last_read_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {
        "project": project,
        "can_write": can_write,
        "my_roles": parts.get(user.get("user_id"), []),
        "participants": [{"user_id": uid, "name": _uname(umap[uid]), "roles": roles} for uid, roles in parts.items()],
        "messages": msgs,
    }


@router.post("/projects/{project_id}/chat")
async def post_chat(project_id: str, body: ChatMessageIn, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    _, umap, parts, can_write = await _access(project_id, user)
    if not can_write:
        raise HTTPException(status_code=403, detail="Solo los participantes del proyecto pueden escribir")
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="El mensaje está vacío")
    now = datetime.now(timezone.utc).isoformat()
    msg = {"message_id": f"pcm_{uuid.uuid4().hex[:10]}", "project_id": project_id, "user_id": user["user_id"],
           "user_name": _uname(umap.get(user["user_id"], user)), "roles": parts[user["user_id"]], "text": text[:4000], "created_at": now}
    await db.project_chat_messages.insert_one({**msg})
    await db.project_chat_reads.update_one({"project_id": project_id, "user_id": user["user_id"]},
                                           {"$set": {"last_read_at": now}}, upsert=True)
    return {**msg, "read_by": []}


def _candidate_query(me: str, umap: dict, mgrs: list) -> dict:
    """Consulta indexada de proyectos donde 'me' puede ser participante (sin recorrer todos)."""
    subs = [uid for uid, u in umap.items() if u.get("supervisor_id") == me]
    subs2 = [uid for uid, u in umap.items() if u.get("supervisor_id") in set(subs)]
    ors = [{"created_by_user_id": {"$in": [me] + subs}}, {"assigned_to_user_id": {"$in": [me] + subs + subs2}}]
    if me in mgrs:
        # Fallback Gerente de Implementación: implementador sin coordinador, o coordinador sin supervisor.
        full_chain = [uid for uid, u in umap.items()
                      if u.get("supervisor_id") in umap and umap[u["supervisor_id"]].get("supervisor_id") in umap]
        ors.append({"assigned_to_user_id": {"$nin": full_chain}})
    return {"$or": ors}


@router.get("/projects-chat/summary")
async def chat_summary(authorization: Optional[str] = Header(None)):
    """Revisión liviana: proyectos donde participo (consulta indexada) + no leídos. Admin ve el resto en solo lectura."""
    user = await get_current_user(authorization)
    me = user.get("user_id")
    umap = await _users_map()
    mgrs = _impl_managers(umap)
    cands = await db.projects.find(_candidate_query(me, umap, mgrs),
                                   {"_id": 0, "project_id": 1, "created_by_user_id": 1, "assigned_to_user_id": 1}).to_list(None)
    mine = [p["project_id"] for p in cands if me in participants(p, umap, mgrs)]
    reads = {r["project_id"]: r.get("last_read_at", "") for r in await db.project_chat_reads.find(
        {"user_id": me}, {"_id": 0, "project_id": 1, "last_read_at": 1}).to_list(None)}
    unread: dict = {}
    if mine:
        async for g in db.project_chat_messages.aggregate([
            {"$match": {"project_id": {"$in": mine}, "user_id": {"$ne": me}}},
            {"$group": {"_id": "$project_id", "last": {"$max": "$created_at"}, "dates": {"$push": "$created_at"}}},
        ]):
            last_read = reads.get(g["_id"], "")
            if g["last"] > last_read:
                unread[g["_id"]] = sum(1 for d in g["dates"] if d > last_read)
    return {"admin": user.get("role") == "admin", "rw": mine, "unread": unread}
