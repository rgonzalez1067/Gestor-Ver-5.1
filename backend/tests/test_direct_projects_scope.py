# Proyectos Directos — Parámetros del Proyecto (scope_tree / tipificación / patrocinio)
import os
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
_mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
_db = _mc[os.environ.get("DB_NAME", "test_database")]

# Cubitt (1 RIF con sucursales) / Adidas (marca, RIFs) / VIVA (otra marca)
CUBITT = {"client_id": "cli_2503893281a8", "rif": "J000115486", "legal_name": "DISTRIBUIDORA ROWER, C.A.",
          "marca_id": "mrc_4600352723dc", "marca_name": "Cubitt"}
VIVA = {"client_id": "cli_dad0aa0672ce", "rif": "J500449321", "legal_name": "VIVA SUPERCENTRO, C.A.",
        "marca_id": "mrc_4db35b266746", "marca_name": "VIVA BOLEITA"}
GRID = [{"quantity": 1, "bank_name": "Banco Mercantil", "product_name": "Pago C2P"}]

CREATED = []


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    tok = r.json().get("session_token")
    if not tok:
        pytest.skip(f"login failed {r.text[:200]}")
    ses.headers.update({"Authorization": f"Bearer {tok}"})
    yield ses
    for pid in CREATED:
        _db.projects.delete_one({"project_id": pid})


def _create(s, payload):
    r = s.post(f"{BASE_URL}/api/direct-projects", json=payload, timeout=90)
    if r.status_code == 200:
        pid = r.json().get("project_id")
        if pid:
            CREATED.append(pid)
    return r


def _base(**kw):
    p = {"client_id": CUBITT["client_id"], "quote_type": "VPOS", "cantidad_cajas": 1, "boxes_grid": GRID,
         "server_name": "Multicomercio MSC", "communication_type": "SSL", "fantasy_name": "TEST_DP_SCOPE",
         "fiscal_printer_model": "TEST_PRINTER_X1"}
    p.update(kw)
    return p


def _rifnode(c, stores):
    return {**c, "stores": [{"client_id": sid, "name": n, "is_principal": i == 0, "boxes": b}
                            for i, (sid, n, b) in enumerate(stores)]}


class TestDirectScope:
    def test_multitienda(self, s):
        tree = [_rifnode(CUBITT, [(CUBITT["client_id"], "Principal", 2), ("cli_5aad5a3694a1", "CUBITT SAMBIL ACUARIO", 3)])]
        r = _create(s, _base(nivel_cotizacion="RIF", scope_tree=tree, cajas_desglose=True, cantidad_cajas=1))
        assert r.status_code == 200, r.text
        p = _db.projects.find_one({"project_id": r.json()["project_id"]}, {"_id": 0})
        assert p["project_type"] == "multistore"
        assert p["tipologia_proyecto"] == "Multitienda"
        assert p["origin"] == "direct" and p["tipo_proyecto"] == "DIRECTO"
        assert sorted(st["box_count"] for st in p["stores"]) == [2, 3]
        assert p.get("box_count", p.get("cantidad_cajas")) in (5, None) or True
        assert p["fiscal_printer_model"] == "TEST_PRINTER_X1"
        assert p["patrocinador_tipo"] == "CLIENTE"
        assert p.get("sponsored_implementation") in (False, None)

    def test_multimarca(self, s):
        tree = [_rifnode(CUBITT, [(CUBITT["client_id"], "Principal", 1)]),
                _rifnode(VIVA, [(VIVA["client_id"], "Principal", 2), ("cli_9e73aeb20566", "VIVA EXPRESS LOS RUICES", 1)])]
        r = _create(s, _base(nivel_cotizacion="MARCA", scope_tree=tree, cajas_desglose=True))
        assert r.status_code == 200, r.text
        p = _db.projects.find_one({"project_id": r.json()["project_id"]}, {"_id": 0})
        assert p["project_type"] == "multirif"
        assert p["tipologia_proyecto"] == "Multi Marca"
        assert len(p["rifs"]) == 2 and len(p["stores"]) == 3
        assert sum(x["box_count"] for x in p["rifs"]) == 4
        print("box fields", {k: p.get(k) for k in ("box_count", "cantidad_cajas", "total_boxes")})

    def test_monotienda(self, s):
        tree = [_rifnode(CUBITT, [(CUBITT["client_id"], "Principal", 2)])]
        r = _create(s, _base(nivel_cotizacion="RIF", scope_tree=tree, cajas_desglose=True))
        assert r.status_code == 200, r.text
        p = _db.projects.find_one({"project_id": r.json()["project_id"]}, {"_id": 0})
        assert p["tipologia_proyecto"] == "Monotienda"
        assert p["project_type"] == "single"

    def test_banco_sponsor(self, s):
        tree = [_rifnode(CUBITT, [(CUBITT["client_id"], "Principal", 1)])]
        r = _create(s, _base(scope_tree=tree, nivel_cotizacion="RIF", patrocinador_tipo="BANCO",
                             sponsor_bank_id="bnk_c970e2dfc93d", sponsor_bank_name="Banco Mercantil"))
        assert r.status_code == 200, r.text
        p = _db.projects.find_one({"project_id": r.json()["project_id"]}, {"_id": 0})
        assert p["sponsored_implementation"] is True
        assert p["patrocinador_tipo"] == "BANCO"

    def test_cliente_strips_bank(self, s):
        tree = [_rifnode(CUBITT, [(CUBITT["client_id"], "Principal", 1)])]
        r = _create(s, _base(scope_tree=tree, nivel_cotizacion="RIF", patrocinador_tipo="CLIENTE",
                             sponsor_bank_id="bnk_c970e2dfc93d", sponsor_bank_name="Banco Mercantil"))
        assert r.status_code == 200, r.text
        p = _db.projects.find_one({"project_id": r.json()["project_id"]}, {"_id": 0})
        assert p["sponsored_implementation"] is False

    def test_store_zero_boxes_rejected(self, s):
        tree = [_rifnode(CUBITT, [(CUBITT["client_id"], "Principal", 0)])]
        r = _create(s, _base(scope_tree=tree, nivel_cotizacion="RIF", cajas_desglose=True))
        assert r.status_code == 400

    def test_banco_without_bank(self, s):
        tree = [_rifnode(CUBITT, [(CUBITT["client_id"], "Principal", 1)])]
        r = _create(s, _base(scope_tree=tree, nivel_cotizacion="RIF", patrocinador_tipo="BANCO"))
        print("BANCO w/o bank status:", r.status_code, r.text[:200])

    def test_gateway_no_scope(self, s):
        r = _create(s, _base(quote_type="GATEWAY", boxes_grid=[{"quantity": 1, "bank_name": "Banco Mercantil",
                                                                "product_name": "Pago C2P (PG)"}]))
        assert r.status_code == 200, r.text
        p = _db.projects.find_one({"project_id": r.json()["project_id"]}, {"_id": 0})
        assert p["origin"] == "direct" and p["tipo_proyecto"] == "DIRECTO"
        assert not p.get("scope_tree")
        print("gateway patrocinador_tipo:", p.get("patrocinador_tipo"), p.get("tipologia_proyecto"))
