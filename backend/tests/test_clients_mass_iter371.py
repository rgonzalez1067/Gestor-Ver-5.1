# Iter371: Mantenimiento Masivo de Sucursales — POST /api/clients/mass-action (requires ui_fixture_iter371_mass.py setup)
import os
import subprocess

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
KH = {"email": "kherrera@megasoft.com.ve", "password": "Kherrera2026*Qa"}
HERE = os.path.dirname(__file__)
IDS3 = ["cli_testmm_1", "cli_testmm_2", "cli_testmm_3"]


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
    if r.status_code != 200 or "session_token" not in r.json():
        pytest.skip(f"login failed {creds['email']}: {r.text[:200]}")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['session_token']}"})
    return s


def _kh(cmd):
    subprocess.run(["python", os.path.join(HERE, "kherrera_iter371.py"), cmd], check=True, capture_output=True)


@pytest.fixture(scope="module", autouse=True)
def data():
    subprocess.run(["python", os.path.join(HERE, "ui_fixture_iter371_mass.py"), "setup"], check=True)
    _kh("reset")
    yield
    _kh("revoke")
    subprocess.run(["python", os.path.join(HERE, "ui_fixture_iter371_mass.py"), "cleanup"], check=True)


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


def _get(admin, cid):
    r = admin.get(f"{BASE_URL}/api/clients/{cid}")
    return r


def _mass(s, action, ids, payload):
    return s.post(f"{BASE_URL}/api/clients/mass-action", json={"action": action, "client_ids": ids, "payload": payload})


# Security: non-admin without/with special permission
class TestSecurity:
    def test_no_perm_403(self):
        _kh("revoke")
        s = _login(KH)
        r = _mass(s, "segment", ["cli_testmm_4"], {"segment": "Corporativo"})
        assert r.status_code == 403
        assert "Mantenimiento Masivo" in r.json()["detail"]

    def test_with_perm_200(self, admin):
        _kh("grant")
        s = _login(KH)
        r = _mass(s, "segment", ["cli_testmm_4"], {"segment": "Corporativo"})
        assert r.status_code == 200, r.text
        assert r.json()["processed"] == 1
        _kh("revoke")

    def test_catalog_has_special(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/permission-catalog")
        assert r.status_code == 200
        txt = r.text
        assert "clientes:mantenimiento_masivo" in txt and "clientes_menu" in txt and "marcas" in txt


# Group & Brand
class TestGroupBrand:
    def test_brand_must_belong_to_group(self, admin):
        r = _mass(admin, "group_brand", IDS3, {"grupo_economico_id": "grp_testmm01", "marca_id": "mrc_testmm_b1"})
        assert r.status_code == 400

    def test_group_brand_applied(self, admin):
        r = _mass(admin, "group_brand", IDS3, {"grupo_economico_id": "grp_testmm01", "marca_id": "mrc_testmm_a2"})
        assert r.status_code == 200, r.text
        assert r.json()["processed"] == 3 and r.json()["skipped"] == []
        for cid in IDS3:
            c = _get(admin, cid).json()
            assert c["marca_id"] == "mrc_testmm_a2"
            assert c["grupo_economico_id"] == "grp_testmm01"
            assert c.get("fantasy_name") == "TEST_MM Marca Dos", c.get("fantasy_name")

    def test_audit_trails_update(self, admin):
        for cid in IDS3:
            r = admin.get(f"{BASE_URL}/api/audit-trails", params={"registro": cid, "action": "UPDATE"})
            assert r.status_code == 200, r.text
            assert r.json()["total"] >= 1, f"no UPDATE audit for {cid}"


# Integrador & Aplicativo
class TestIntegrador:
    def test_integrador_applied(self, admin):
        r = _mass(admin, "integrador", IDS3, {"integrador_id": "int_testmm_a2", "aplicativo": "TEST_MM App A2"})
        assert r.status_code == 200, r.text
        c = _get(admin, "cli_testmm_1").json()
        assert c["integrador_id"] == "int_testmm_a2" and c["aplicativo"] == "TEST_MM App A2"
        assert c["integrador_name"] == "TEST_MM Integrador A"

    def test_integrador_invalid(self, admin):
        r = _mass(admin, "integrador", IDS3, {"integrador_id": "int_nope", "aplicativo": "x"})
        assert r.status_code == 400


# Simple actions smoke
class TestSimple:
    def test_segment(self, admin):
        assert _mass(admin, "segment", ["cli_testmm_5"], {"segment": "Mixto"}).status_code == 200
        c = _get(admin, "cli_testmm_5").json()
        assert c["segment"] == "Mixto" and "segment" in c["inherit_overrides"]

    def test_ejecutivo(self, admin):
        assert _mass(admin, "ejecutivo", ["cli_testmm_5"], {"ejecutivo_user_id": "user_e6ad4edb546f"}).status_code == 200
        c = _get(admin, "cli_testmm_5").json()
        assert c["ejecutivo_user_id"] == "user_e6ad4edb546f" and c["ejecutivo_propietario"]

    def test_categoria(self, admin):
        assert _mass(admin, "categoria", ["cli_testmm_5"], {"categoria_comercial": "TEST_MM Cat"}).status_code == 200
        assert _get(admin, "cli_testmm_5").json()["categoria_comercial"] == "TEST_MM Cat"

    def test_coord_only(self, admin):
        before = _get(admin, "cli_testmm_5").json().get("implementer_user_id")
        r = _mass(admin, "coord_impl", ["cli_testmm_5"], {"apply_coordinator": True, "coordinator_user_id": "user_e6ad4edb546f",
                                                          "apply_implementer": False, "implementer_user_id": "user_4f7c4697b820"})
        assert r.status_code == 200
        c = _get(admin, "cli_testmm_5").json()
        assert c["coordinator_user_id"] == "user_e6ad4edb546f"
        assert c.get("implementer_user_id") == before

    def test_coord_none_400(self, admin):
        assert _mass(admin, "coord_impl", ["cli_testmm_5"], {}).status_code == 400

    def test_tipo_servicio(self, admin):
        assert _mass(admin, "tipo_servicio", ["cli_testmm_5"], {"tipo_servicio": ["MPOS", "Link de Pago"]}).status_code == 200
        assert _get(admin, "cli_testmm_5").json()["tipo_servicio"] == ["MPOS", "Link de Pago"]

    def test_bad_action_and_empty(self, admin):
        assert _mass(admin, "foo", ["cli_testmm_5"], {}).status_code == 400
        assert _mass(admin, "segment", [], {"segment": "Mixto"}).status_code == 400


# Delete with dependency skip
class TestDelete:
    def test_confirm_required(self, admin):
        assert _mass(admin, "delete", ["cli_testmm_4"], {"confirm": "eliminar"}).status_code == 400

    def test_delete_skips_active_project(self, admin):
        r = _mass(admin, "delete", ["cli_testmm_4", "cli_testmm_5", "cli_testmm_6"], {"confirm": "ELIMINAR"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["processed"] == 2
        assert len(d["skipped"]) == 1 and d["skipped"][0]["client_id"] == "cli_testmm_6"
        assert "Proyecto en ejecución" in d["skipped"][0]["reasons"]
        assert _get(admin, "cli_testmm_4").status_code == 404
        assert _get(admin, "cli_testmm_6").status_code == 200
        r = admin.get(f"{BASE_URL}/api/audit-trails", params={"registro": "cli_testmm_4", "action": "DELETE"})
        assert r.json()["total"] >= 1
