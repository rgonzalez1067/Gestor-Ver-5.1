# Fixture iter390: empresa QA con aplicativo sin referencias + empresa QA vacía. Uso: python ui_fixture_iter390_maint.py create|cleanup
import os, sys, asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
EMP, EMPTY, APP = "emp_qa390ui", "emp_qa390empty", "int_qa390ui"


async def create():
    now = datetime.now(timezone.utc).isoformat()
    for eid, name in ((EMP, "QA UI 390 Empresa"), (EMPTY, "QA UI 390 Vacia")):
        await db.empresas_integradoras.replace_one({"empresa_id": eid}, {"empresa_id": eid, "tipo_persona": "Jurídica", "razon_social": name,
                                                   "norm_name": name.lower(), "rif": None, "contacts": [], "created_at": now}, upsert=True)
    await db.integrators.replace_one({"integrator_id": APP}, {"integrator_id": APP, "name": "QA UI 390 Empresa", "app_name": "QA Duplicado UI",
                                     "integrator_type": "Integrador", "integration_type": "CR", "integrator_status": "En proceso",
                                     "empresa_integradora_id": EMP, "created_at": now}, upsert=True)
    print("created")


async def cleanup():
    r1 = await db.integrators.delete_many({"integrator_id": APP})
    r2 = await db.empresas_integradoras.delete_many({"empresa_id": {"$in": [EMP, EMPTY]}})
    r3 = await db.integrator_certificates.delete_many({"integrator_id": APP})
    print("deleted", r1.deleted_count, r2.deleted_count, r3.deleted_count)

asyncio.run(create() if sys.argv[1] == "create" else cleanup())
