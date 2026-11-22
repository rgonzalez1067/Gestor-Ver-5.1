# Fixture iter387: copias TEST_ de aplicativos certificados (bloqueo + certificados). Uso: python ui_fixture_iter387_locks.py create|cleanup
import os, sys, asyncio, json, copy
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
SRC = "int_f6cbdce034f9"
IDS = {"locked": "int_test387lock", "active": "int_test387actv", "notpl": "int_test387notp", "closed": "int_test387clos"}


async def create():
    src = await db.integrators.find_one({"integrator_id": SRC}, {"_id": 0})
    for key, iid in IDS.items():
        d = copy.deepcopy(src)
        d.update({"integrator_id": iid, "app_name": f"TEST_QA387 {key}", "cert_outdated": None})
        if key == "active":
            d.update({"project_scope": "new", "integrator_status": "En proceso"})
        if key == "notpl":
            d.update({"implementador_user_id": "user_qaeditor01", "implementador": "QA Editor"})
        if key == "closed":
            d.update({"integrator_status": "Cerrado"})
        await db.integrators.replace_one({"integrator_id": iid}, d, upsert=True)
    print(json.dumps(IDS))


async def cleanup():
    ids = list(IDS.values())
    r1 = await db.integrators.delete_many({"integrator_id": {"$in": ids}})
    r2 = await db.integrator_certificates.delete_many({"integrator_id": {"$in": ids}})
    r3 = await db.bitacora.delete_many({"integrator_id": {"$in": ids}})
    print("deleted", r1.deleted_count, r2.deleted_count, r3.deleted_count)

asyncio.run(create() if sys.argv[1] == "create" else cleanup())
