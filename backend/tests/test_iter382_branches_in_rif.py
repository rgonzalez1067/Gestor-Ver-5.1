# Iter 382: Sucursales as a tab inside the RIF file (Razón Social): branch CRUD, branch-data PUT, contact inheritance, RBAC name
import os
import random
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
STATE = {}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=30)
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {r.status_code}")
    sess.headers.update({"Authorization": f"Bearer {r.json()['session_token']}", "Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module", autouse=True)
def principal(s):
    rif = f"J{random.randint(400000000, 499999999)}"
    r = s.post(f"{BASE_URL}/api/clients", json={
        "rif": rif, "legal_name": "TEST_QA RAZON SOCIAL 382, CA.", "fantasy_name": "TEST_QA382",
        "contacts": [{"full_name": "Contacto RIF QA", "email": "rif.qa382@empresa.com", "phone": "0212", "role": "Administrativo"}],
    }, timeout=30)
    assert r.status_code == 200, r.text
    p = r.json()
    STATE["p"] = p
    STATE["branches"] = []
    yield p
    for bid in STATE["branches"]:
        s.delete(f"{BASE_URL}/api/clients/{bid}", timeout=15)
    d = s.delete(f"{BASE_URL}/api/clients/{p['client_id']}", timeout=15)
    print("cleanup principal", d.status_code, d.text[:120])


class TestRBAC:
    def test_catalog_clientes_named_razon_social(self, s):
        import importlib.util, sys
        sys.path.insert(0, "/app/backend")
        import permissions_catalog as pc
        txt = repr(vars(pc))
        assert "'Razón Social'" in txt
        assert "clientes:mantenimiento_masivo" in txt


class TestBranchCRUD:
    def test_validation_principal_name(self, s):
        r = s.post(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}/branches",
                   json={"sucursal": "Principal", "branch_address": "x", "cantidad_cajas": 1})
        assert r.status_code == 400

    def test_validation_missing_address_and_cajas_backend(self, s):
        # Requirement: dirección y cajas>=1 obligatorias. Check that backend enforces it on create.
        r = s.post(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}/branches",
                   json={"sucursal": "TEST_NoAddr QA", "branch_address": "", "cantidad_cajas": 0})
        if r.status_code == 200:
            STATE["branches"].append(r.json()["client_id"])
        assert r.status_code == 400, f"backend accepted branch without address/cajas: {r.status_code}"

    def test_create_tienda_norte_with_contact(self, s):
        r = s.post(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}/branches", json={
            "sucursal": "Tienda Norte QA", "branch_address": "Av Norte 1", "cantidad_cajas": 3,
            "contacts": [{"full_name": "Gerente Norte", "role": "Operativo", "phone": "0414", "email": "gerente.norte@empresa.com"}]})
        assert r.status_code == 200, r.text
        b = r.json()
        STATE["branches"].append(b["client_id"]); STATE["norte"] = b["client_id"]
        assert b["is_branch"] is True and b["parent_client_id"] == STATE["p"]["client_id"]
        assert b["rif"] == STATE["p"]["rif"] and b["cantidad_cajas"] == 3
        assert b["branch_address"] == "Av Norte 1"
        assert [c["email"] for c in b["contacts"]] == ["gerente.norte@empresa.com"]

    def test_create_tienda_sur_no_contacts(self, s):
        r = s.post(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}/branches", json={
            "sucursal": "Tienda Sur QA", "branch_address": "Av Sur 2", "cantidad_cajas": 2, "contacts": []})
        assert r.status_code == 200, r.text
        b = r.json()
        STATE["branches"].append(b["client_id"]); STATE["sur"] = b["client_id"]
        assert b["cantidad_cajas"] == 2 and b["contacts"] == []

    def test_duplicate_name_rejected(self, s):
        r = s.post(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}/branches",
                   json={"sucursal": "Tienda Sur QA", "branch_address": "x", "cantidad_cajas": 1})
        assert r.status_code == 400

    def test_branches_endpoint(self, s):
        r = s.get(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}/branches")
        assert r.status_code == 200
        d = r.json()
        names = {b["sucursal"]: b for b in d["branches"]}
        assert {"Tienda Norte QA", "Tienda Sur QA"} <= set(names)
        assert names["Tienda Norte QA"]["cantidad_cajas"] == 3 and names["Tienda Sur QA"]["cantidad_cajas"] == 2
        assert d["principal"]["client_id"] == STATE["p"]["client_id"]

    def test_update_branch_data_and_persist(self, s):
        bid = STATE["sur"]
        r = s.put(f"{BASE_URL}/api/clients/{bid}/branch-data", json={
            "sucursal": "Tienda Sur QA", "branch_address": "Av Sur 2 editada", "cantidad_cajas": 4, "contacts": []})
        assert r.status_code == 200, r.text
        assert r.json()["cantidad_cajas"] == 4
        g = s.get(f"{BASE_URL}/api/clients/{bid}").json()
        assert g["branch_address"] == "Av Sur 2 editada" and g["cantidad_cajas"] == 4
        # restore 2
        s.put(f"{BASE_URL}/api/clients/{bid}/branch-data", json={
            "sucursal": "Tienda Sur QA", "branch_address": "Av Sur 2", "cantidad_cajas": 2, "contacts": []})

    def test_update_branch_data_validations(self, s):
        bid = STATE["sur"]
        assert s.put(f"{BASE_URL}/api/clients/{bid}/branch-data", json={"sucursal": "principal", "cantidad_cajas": 1}).status_code == 400
        assert s.put(f"{BASE_URL}/api/clients/{bid}/branch-data", json={"sucursal": "X QA", "branch_address": "a", "cantidad_cajas": 0}).status_code == 400
        assert s.put(f"{BASE_URL}/api/clients/{bid}/branch-data", json={"sucursal": "Tienda Norte QA", "branch_address": "a", "cantidad_cajas": 1}).status_code == 400
        assert s.put(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}/branch-data", json={"sucursal": "X", "cantidad_cajas": 1}).status_code == 404

    def test_update_branch_data_requires_address(self, s):
        r = s.put(f"{BASE_URL}/api/clients/{STATE['sur']}/branch-data", json={"sucursal": "Tienda Sur QA", "branch_address": "", "cantidad_cajas": 2})
        if r.status_code == 200:
            s.put(f"{BASE_URL}/api/clients/{STATE['sur']}/branch-data", json={"sucursal": "Tienda Sur QA", "branch_address": "Av Sur 2", "cantidad_cajas": 2})
        assert r.status_code == 400, "backend accepted empty branch_address on branch-data"


class TestInheritance:
    def test_sur_inherits_rif_contacts(self, s):
        r = s.get(f"{BASE_URL}/api/clients/{STATE['sur']}/consolidated-contacts")
        assert r.status_code == 200, r.text
        emails = [c.get("email") for c in r.json()["contacts"]]
        print("sur consolidated", emails)
        assert "rif.qa382@empresa.com" in emails
        inh = s.get(f"{BASE_URL}/api/clients/{STATE['sur']}/inheritance")
        assert inh.status_code == 200
        print("sur inheritance keys", list(inh.json().keys()))
        assert "rif.qa382@empresa.com" in str(inh.json())

    def test_norte_own_contact(self, s):
        r = s.get(f"{BASE_URL}/api/clients/{STATE['norte']}/consolidated-contacts")
        assert r.status_code == 200
        emails = [c.get("email") for c in r.json()["contacts"]]
        print("norte consolidated", emails)
        assert "gerente.norte@empresa.com" in emails
        inh = s.get(f"{BASE_URL}/api/clients/{STATE['norte']}/inheritance").json()
        assert "gerente.norte@empresa.com" in str(inh)


class TestDelete:
    def test_delete_principal_blocked_with_branches(self, s):
        r = s.delete(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}")
        assert r.status_code == 400

    def test_delete_branch(self, s):
        r = s.post(f"{BASE_URL}/api/clients/{STATE['p']['client_id']}/branches",
                   json={"sucursal": "TEST_Borrar QA", "branch_address": "x", "cantidad_cajas": 1})
        assert r.status_code == 200
        bid = r.json()["client_id"]
        d = s.delete(f"{BASE_URL}/api/clients/{bid}")
        assert d.status_code == 200
        assert s.get(f"{BASE_URL}/api/clients/{bid}").status_code == 404
