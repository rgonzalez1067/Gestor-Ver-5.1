# Fixture iter371: Mantenimiento Masivo de Sucursales (TEST_MM data). Usage: python ui_fixture_iter371_mass.py setup|cleanup
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
from pymongo import MongoClient  # noqa: E402

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
NOW = datetime.now(timezone.utc).isoformat()

GROUPS = [{"group_id": "grp_testmm01", "name": "TEST_MM Grupo Alfa"}, {"group_id": "grp_testmm02", "name": "TEST_MM Grupo Beta"}]
BRANDS = [
    {"brand_id": "mrc_testmm_a1", "name": "TEST_MM Marca Uno", "group_id": "grp_testmm01"},
    {"brand_id": "mrc_testmm_a2", "name": "TEST_MM Marca Dos", "group_id": "grp_testmm01"},
    {"brand_id": "mrc_testmm_b1", "name": "TEST_MM Marca Beta", "group_id": "grp_testmm02"},
]
INTEGRATORS = [
    {"integrator_id": "int_testmm_a1", "name": "TEST_MM Integrador A", "app_name": "TEST_MM App A1"},
    {"integrator_id": "int_testmm_a2", "name": "TEST_MM Integrador A", "app_name": "TEST_MM App A2"},
    {"integrator_id": "int_testmm_b1", "name": "TEST_MM Integrador B", "app_name": "TEST_MM App B1"},
]
CLIENT_IDS = [f"cli_testmm_{i}" for i in range(1, 7)]


def client(i):
    return {"client_id": f"cli_testmm_{i}", "rif": f"J9500000{i:02d}", "legal_name": f"TEST_MM Empresa {i}, C.A.",
            "fantasy_name": f"TEST_MM Fantasia {i}", "segment": "Pymes", "sucursal": "Principal", "is_branch": False,
            "parent_client_id": None, "condicion": "Cliente", "tipo_servicio": ["VPOS"], "contacts": [],
            "inherit_overrides": [], "created_at": NOW}


def setup():
    cleanup()
    for g in GROUPS:
        db.economic_groups.insert_one({**g, "description": "", "contacts": [], "representantes": [], "created_at": NOW})
    for b in BRANDS:
        db.brands.insert_one({**b, "description": "", "characteristics": {}, "contacts": [], "created_at": NOW})
    for it in INTEGRATORS:
        db.integrators.insert_one({**it, "created_at": NOW})
    for i in range(1, 7):
        db.clients.insert_one(client(i))
    db.projects.insert_one({"project_id": "prj_testmm_1", "client_id": "cli_testmm_6", "status": "En Gestión",
                            "name": "TEST_MM Proyecto", "created_at": NOW})
    print("setup ok")


def cleanup():
    db.economic_groups.delete_many({"group_id": {"$in": [g["group_id"] for g in GROUPS]}})
    db.brands.delete_many({"brand_id": {"$in": [b["brand_id"] for b in BRANDS]}})
    db.integrators.delete_many({"integrator_id": {"$in": [i["integrator_id"] for i in INTEGRATORS]}})
    db.clients.delete_many({"client_id": {"$in": CLIENT_IDS}})
    db.projects.delete_many({"project_id": "prj_testmm_1"})
    print("cleanup ok")


if __name__ == "__main__":
    {"setup": setup, "cleanup": cleanup}[sys.argv[1]]()
