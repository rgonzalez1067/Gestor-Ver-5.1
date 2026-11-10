# Fixture iter373: reset QA passwords, grant temporary quote_history, clone TEST_ projects (direct CORP + multistore) for cobro/master-override.
import asyncio, os, sys, json, copy
from datetime import datetime, timezone
sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from config import hash_password

STATE = '/tmp/iter373_state.json'
PWD = 'QaMegaSoft2026*x'


async def setup(db):
    state = {"users": {}, "projects": []}
    now = datetime.now(timezone.utc).isoformat()
    for e in ["jdolande@megasoft.com.ve", "mmartin@megasoft.com.ve"]:
        u = await db.users.find_one({"email": e}, {"_id": 0})
        state["users"][e] = {"qh": (u.get("permissions") or {}).get("quote_history", "none")}
        await db.users.update_one({"email": e}, {"$set": {
            "password_hash": hash_password(PWD), "must_change_password": False,
            "password_changed_at": now, "failed_login_attempts": 0, "account_status": "ACTIVE",
            "permissions.quote_history": "read" if state["users"][e]["qh"] == "none" else state["users"][e]["qh"]}})
    src_direct = await db.projects.find_one({"origin": "direct", "client_segment": "CORP", "project_type": {"$nin": ["multistore", "multirif"]}}, {"_id": 0})
    src_ms = await db.projects.find_one({"project_type": "multistore", "stores.1": {"$exists": True}}, {"_id": 0})
    for tag, src in (("direct", src_direct), ("ms", src_ms)):
        d = copy.deepcopy(src)
        d["project_id"] = f"prj_test373_{tag}"
        d["project_number"] = f"TEST_373_{tag.upper()}"
        d["client_name"] = f"TEST_373 {tag}"
        d["cobro_recurrente_status"] = False
        d["notes"] = []
        d["bitacora"] = []
        if tag == "ms":
            d["status"] = "En Gestión"
        await db.projects.delete_one({"project_id": d["project_id"]})
        await db.projects.insert_one(d)
        state["projects"].append(d["project_id"])
        print(tag, d["project_id"], "src", src["project_id"], d.get("client_segment"), d.get("origin"))
    json.dump(state, open(STATE, 'w'))


async def cleanup(db):
    state = json.load(open(STATE))
    for e, s in state["users"].items():
        await db.users.update_one({"email": e}, {"$set": {"permissions.quote_history": s["qh"]}})
    for pid in state["projects"]:
        r = await db.projects.delete_one({"project_id": pid})
        print("deleted", pid, r.deleted_count)


async def main():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    await {"setup": setup, "cleanup": cleanup}[sys.argv[1]](db)

asyncio.run(main())
