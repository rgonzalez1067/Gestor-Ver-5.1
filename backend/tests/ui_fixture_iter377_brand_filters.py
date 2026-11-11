# Iter377: fixture for /marcas filters (Grupo/Ejecutivo/Segmento). Usage: python ui_fixture_iter377_brand_filters.py setup|cleanup
import os
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

EJ1 = {"ejecutivo_user_id": "usr_test377_ej1", "ejecutivo_propietario": "TEST_377 Ejecutivo Uno"}
EJ2 = {"ejecutivo_user_id": "usr_test377_ej2", "ejecutivo_propietario": "TEST_377 Ejecutivo Dos"}
GROUPS = [
    {"group_id": "grp_test377_a", "name": "TEST_377 Grupo A", "characteristics": {}},
    {"group_id": "grp_test377_b", "name": "TEST_377 Grupo B", "characteristics": {}},
]
BRANDS = [
    {"brand_id": "brd_test377_1", "name": "TEST_377 Alfa", "group_id": "grp_test377_a", "characteristics": {"segment": "Pymes", **EJ1}},
    {"brand_id": "brd_test377_2", "name": "TEST_377 Beta", "group_id": "grp_test377_a", "characteristics": {}},
    {"brand_id": "brd_test377_3", "name": "TEST_377 Gamma", "group_id": "grp_test377_b", "characteristics": {"segment": "Mixto"}},
    {"brand_id": "brd_test377_4", "name": "TEST_377 Delta", "group_id": None, "characteristics": {}},
]


def _cli(cid, rif, brand, extra):
    return {"client_id": cid, "rif": rif, "legal_name": f"TEST_377 {cid}", "marca_id": brand["brand_id"],
            "marca_name": brand["name"], "fantasy_name": brand["name"], "is_branch": False, "parent_client_id": None,
            "inherit_overrides": [], "tipo_servicio": [], "contacts": [], **extra}


CLIENTS = [
    _cli("cli_test377_r2a", "J-37700002-1", BRANDS[1], {"segment": "Corporativo", **EJ2}),
    _cli("cli_test377_r2b", "J-37700002-2", BRANDS[1], {"segment": None, "ejecutivo_propietario": "TEST_377 SoloNombre"}),
    _cli("cli_test377_r3", "J-37700003-1", BRANDS[2], {"segment": "Pymes", **EJ1}),
]


def cleanup():
    db.clients.delete_many({"client_id": {"$in": [c["client_id"] for c in CLIENTS]}})
    db.brands.delete_many({"brand_id": {"$in": [b["brand_id"] for b in BRANDS]}})
    db.economic_groups.delete_many({"group_id": {"$in": [g["group_id"] for g in GROUPS]}})


def setup():
    cleanup()
    db.economic_groups.insert_many([dict(g) for g in GROUPS])
    db.brands.insert_many([dict(b) for b in BRANDS])
    db.clients.insert_many([dict(c) for c in CLIENTS])


if __name__ == "__main__":
    {"setup": setup, "cleanup": cleanup}[sys.argv[1]]()
    print("ok", sys.argv[1])
