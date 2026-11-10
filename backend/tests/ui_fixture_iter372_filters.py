# Fixture iter372: Clients Ejecutivo/Implementador multiselect filters (TEST_FLT data). Usage: python ui_fixture_iter372_filters.py setup|cleanup|show
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from pymongo import MongoClient  # noqa: E402

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
NOW = datetime.now(timezone.utc).isoformat()
SPEC = [  # (ejecutivo, implementer, segment)
    ("TEST_FLT Ejec Alfa", "TEST_FLT Impl Uno", "Pymes"),
    ("TEST_FLT Ejec Alfa", "TEST_FLT Impl Dos", "Pymes"),
    ("TEST_FLT Ejec Beta", "TEST_FLT Impl Uno", "Corporativo"),
    ("TEST_FLT Ejec Beta", None, "Pymes"),
]
IDS = [f"cli_testflt_{i}" for i in range(1, len(SPEC) + 1)]


def setup():
    cleanup()
    for i, (ej, im, seg) in enumerate(SPEC, 1):
        db.clients.insert_one({"client_id": f"cli_testflt_{i}", "rif": f"J9600000{i:02d}", "legal_name": f"TEST_FLT Empresa {i}, C.A.",
                               "fantasy_name": f"TEST_FLT Fantasia {i}", "segment": seg, "sucursal": "Principal", "is_branch": False,
                               "parent_client_id": None, "condicion": "Cliente", "tipo_servicio": ["VPOS"], "contacts": [],
                               "ejecutivo_propietario": ej, "implementer_name": im, "inherit_overrides": [], "created_at": NOW})
    print("setup ok")


def cleanup():
    db.clients.delete_many({"client_id": {"$in": IDS}})
    print("cleanup ok")


def show():
    for c in db.clients.find({"client_id": {"$in": IDS}}, {"_id": 0, "client_id": 1, "segment": 1, "ejecutivo_propietario": 1, "implementer_name": 1}):
        print(c)


if __name__ == "__main__":
    {"setup": setup, "cleanup": cleanup, "show": show}[sys.argv[1]]()
