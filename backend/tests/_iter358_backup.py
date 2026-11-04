import sys, json, asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util

MONGO_URL = os.environ["MONGO_URL"]; DB_NAME = os.environ["DB_NAME"]
db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
PATH = "/tmp/iter358_backup_{}.json"


async def main(cmd, pid):
    if cmd == "backup":
        d = await db.projects.find_one({"project_id": pid})
        open(PATH.format(pid), "w").write(json_util.dumps(d))
        print("backed up", pid, d.get("project_type"), d.get("box_count"), len(d.get("stores") or []))
    elif cmd == "restore":
        d = json_util.loads(open(PATH.format(pid)).read())
        r = await db.projects.replace_one({"_id": d["_id"]}, d)
        now = await db.projects.find_one({"project_id": pid})
        print("restored", r.modified_count, "identical:", now == d)
    elif cmd == "show":
        d = await db.projects.find_one({"project_id": pid}, {"_id": 0})
        print(json.dumps({k: d.get(k) for k in ["project_type", "box_count", "client_name", "client_sede", "client_id", "implementation_matrix", "stores", "rifs", "contract_baseline"]}, default=str, ensure_ascii=False, indent=1)[:5000])
        print([ (s.get("item_type"), s.get("bank_name"), s.get("item_name"), s.get("cantidad_cajas"), s.get("quantity")) for s in d.get("services") or []])
        print("bitacora last:", (d.get("bitacora") or [{}])[-1].get("text"))
    elif cmd == "inject":
        # inyecta fases completadas en la matriz principal
        d = await db.projects.find_one({"project_id": pid})
        m = d.get("implementation_matrix") or {}
        for bn, prods in m.items():
            for pn in prods:
                prods[pn]["Recibido"] = {"completed": True, "date": "2026-01-10", "by": "TEST_iter358"}
                prods[pn]["Configurado"] = {"completed": True, "date": "2026-01-11", "by": "TEST_iter358"}
        await db.projects.update_one({"project_id": pid}, {"$set": {"implementation_matrix": m}})
        print("injected", json.dumps(m, ensure_ascii=False)[:800])

asyncio.run(main(sys.argv[1], sys.argv[2]))
