# Iter376: Brand mass actions — POST /api/marcas/mass-action (uses ui_fixture_iter376_brand_mass.py)
import os
import subprocess

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
NOPERM = {"email": "jdolande@megasoft.com.ve", "password": "QaMegaSoft2026*x"}
FIX = os.path.join(os.path.dirname(__file__), "ui_fixture_iter376_brand_mass.py")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
    if r.status_code != 200 or "session_token" not in r.json():
        pytest.skip(f"login failed {creds['email']}: {r.text[:200]}")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['session_token']}"})
    return s


@pytest.fixture(scope="module", autouse=True)
def data():
    subprocess.run(["python", FIX, "setup"], check=True)
    yield
    subprocess.run(["python", FIX, "cleanup"], check=True)


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


def _mass(s, action, ids, payload):
    return s.post(f"{BASE_URL}/api/marcas/mass-action", json={"action": action, "brand_ids": ids, "payload": payload})


def _c(cid):
    return db.clients.find_one({"client_id": cid}, {"_id": 0})


# Security / validation
class TestSecurity:
    def test_noperm_403(self):
        s = _login(NOPERM)
        r = _mass(s, "segment", ["brd_test376_1"], {"segment": "Corporativo"})
        assert r.status_code == 403
        assert "Mantenimiento Masivo" in r.json()["detail"]

    def test_tipo_servicio_400(self, admin):
        r = _mass(admin, "tipo_servicio", ["brd_test376_1"], {"tipo_servicio": ["VPOS"]})
        assert r.status_code == 400

    def test_unknown_and_empty_400(self, admin):
        assert _mass(admin, "foo", ["brd_test376_1"], {}).status_code == 400
        assert _mass(admin, "segment", [], {"segment": "Mixto"}).status_code == 400
        assert _mass(admin, "segment", ["brd_test376_1"], {"segment": "XX"}).status_code == 400
        assert _mass(admin, "group", ["brd_test376_1"], {"grupo_economico_id": "nope"}).status_code == 400
        assert _mass(admin, "delete", ["brd_test376_empty"], {"confirm": "no"}).status_code == 400


# Segment propagation honoring inherit_overrides
class TestSegment:
    def test_segment_inherit(self, admin):
        r = _mass(admin, "segment", ["brd_test376_1", "brd_test376_2"], {"segment": "Corporativo"})
        assert r.status_code == 200, r.text
        assert r.json()["processed"] == 2
        for b in ("brd_test376_1", "brd_test376_2"):
            assert db.brands.find_one({"brand_id": b})["characteristics"]["segment"] == "Corporativo"
        assert _c("cli_test376_r1")["segment"] == "Corporativo"
        assert _c("cli_test376_r3")["segment"] == "Corporativo"
        assert _c("cli_test376_r1s")["segment"] == "Corporativo", "branch should inherit from RIF"
        assert _c("cli_test376_r2")["segment"] == "Mixto", "override must be kept"
        assert "segment" not in (_c("cli_test376_r1").get("inherit_overrides") or [])


# Other simple actions persist on brand characteristics
class TestSimpleActions:
    def test_categoria(self, admin):
        cat = db.commercial_categories.find_one({}, {"_id": 0, "name": 1})
        if not cat:
            pytest.skip("no categories")
        r = _mass(admin, "categoria", ["brd_test376_1"], {"categoria_comercial": cat["name"]})
        assert r.status_code == 200, r.text
        assert db.brands.find_one({"brand_id": "brd_test376_1"})["characteristics"]["categoria_comercial"] == cat["name"]
        assert _c("cli_test376_r1")["categoria_comercial"] == cat["name"]

    def test_ejecutivo(self, admin):
        r = _mass(admin, "ejecutivo", ["brd_test376_1"], {"ejecutivo_user_id": "user_admin_main"})
        assert r.status_code == 200, r.text
        ch = db.brands.find_one({"brand_id": "brd_test376_1"})["characteristics"]
        assert ch["ejecutivo_user_id"] == "user_admin_main" and ch["ejecutivo_propietario"]
        assert _c("cli_test376_r1")["ejecutivo_user_id"] == "user_admin_main"
        assert _c("cli_test376_r1s")["ejecutivo_user_id"] == "user_admin_main"

    def test_coord_impl_requires_field(self, admin):
        assert _mass(admin, "coord_impl", ["brd_test376_1"], {}).status_code == 400
        r = _mass(admin, "coord_impl", ["brd_test376_1"], {"apply_coordinator": True, "coordinator_user_id": "user_admin_main"})
        assert r.status_code == 200, r.text
        assert _c("cli_test376_r1")["coordinator_user_id"] == "user_admin_main"

    def test_integrador(self, admin):
        intg = db.integrators.find_one({"app_name": {"$nin": [None, ""]}}, {"_id": 0})
        if not intg:
            pytest.skip("no integrators")
        r = _mass(admin, "integrador", ["brd_test376_1"], {"integrador_id": intg["integrator_id"]})
        assert r.status_code == 200, r.text
        assert _c("cli_test376_r1")["integrador_id"] == intg["integrator_id"]
        assert _c("cli_test376_r1")["aplicativo"] == intg["app_name"]


# Group assignment propagates to RIFs
class TestGroup:
    def test_group(self, admin):
        r = _mass(admin, "group", ["brd_test376_1"], {"grupo_economico_id": "grp_test376_b"})
        assert r.status_code == 200, r.text
        assert db.brands.find_one({"brand_id": "brd_test376_1"})["group_id"] == "grp_test376_b"
        for cid in ("cli_test376_r1", "cli_test376_r2"):
            c = _c(cid)
            assert c["grupo_economico_id"] == "grp_test376_b"
            assert c["grupo_economico"] == "TEST_376 Grupo B"
        assert _c("cli_test376_r3")["grupo_economico_id"] == "grp_test376_a"
        lst = admin.get(f"{BASE_URL}/api/marcas", params={"search": "TEST_376 Marca Uno"}).json()
        assert lst and lst[0]["group_id"] == "grp_test376_b"


# Delete: empty brand deleted, brand with RIF skipped
class TestDelete:
    def test_delete(self, admin):
        r = _mass(admin, "delete", ["brd_test376_empty", "brd_test376_2"], {"confirm": "ELIMINAR"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["processed"] == 1
        assert [s["client_id"] for s in d["skipped"]] == ["brd_test376_2"]
        assert "RIF" in d["skipped"][0]["reasons"][0]
        assert db.brands.find_one({"brand_id": "brd_test376_empty"}) is None
        assert db.brands.find_one({"brand_id": "brd_test376_2"}) is not None
