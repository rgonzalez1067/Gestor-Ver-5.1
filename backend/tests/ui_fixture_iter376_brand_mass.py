# Iter376: fixture for Brand mass actions (TEST_ brands/groups/RIFs). Usage: python ui_fixture_iter376_brand_mass.py setup|cleanup
import os
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

GROUPS = [
    {"group_id": "grp_test376_a", "name": "TEST_376 Grupo A", "characteristics": {}},
    {"group_id": "grp_test376_b", "name": "TEST_376 Grupo B", "characteristics": {}},
]
BRANDS = [
    {"brand_id": "brd_test376_1", "name": "TEST_376 Marca Uno", "group_id": "grp_test376_a", "characteristics": {"segment": "Pymes"}},
    {"brand_id": "brd_test376_2", "name": "TEST_376 Marca Dos", "group_id": "grp_test376_a", "characteristics": {"segment": "Pymes"}},
    {"brand_id": "brd_test376_empty", "name": "TEST_376 Marca Vacia", "group_id": None, "characteristics": {}},
]


def _cli(cid, rif, brand, overrides, segment="Pymes", branch_of=None):
    return {
        "client_id": cid, "rif": rif, "legal_name": f"TEST_376 {cid}", "marca_id": brand["brand_id"],
        "marca_name": brand["name"], "fantasy_name": brand["name"], "grupo_economico_id": "grp_test376_a",
        "grupo_economico": "TEST_376 Grupo A", "is_branch": bool(branch_of), "parent_client_id": branch_of,
        "sucursal": "Suc 1" if branch_of else None, "segment": segment, "inherit_overrides": overrides,
        "tipo_servicio": [], "contacts": [],
    }


CLIENTS = [
    _cli("cli_test376_r1", "J-37600001-1", BRANDS[0], []),
    _cli("cli_test376_r1s", "J-37600001-1", BRANDS[0], [], branch_of="cli_test376_r1"),
    _cli("cli_test376_r2", "J-37600002-2", BRANDS[0], ["segment"], segment="Mixto"),
    _cli("cli_test376_r3", "J-37600003-3", BRANDS[1], []),
]


def cleanup():
    db.clients.delete_many({"client_id": {"$in": [c["client_id"] for c in CLIENTS]}})
    db.brands.delete_many({"brand_id": {"$in": [b["brand_id"] for b in BRANDS] + ["brd_test376_ui_empty"]}})
    db.economic_groups.delete_many({"group_id": {"$in": [g["group_id"] for g in GROUPS]}})


def setup():
    cleanup()
    db.economic_groups.insert_many([dict(g) for g in GROUPS])
    db.brands.insert_many([dict(b) for b in BRANDS])
    db.clients.insert_many([dict(c) for c in CLIENTS])


if __name__ == "__main__":
    {"setup": setup, "cleanup": cleanup}[sys.argv[1]]()
    print("ok", sys.argv[1])
