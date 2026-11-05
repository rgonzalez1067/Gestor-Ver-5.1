# ruff: noqa
"""Iter364 — Pistas de Auditoría (audit_trails): interceptor CREATE/UPDATE/DELETE,
aislamiento Proyectos, API de consulta/filtros/export, RBAC auditor, login/password."""
import io
import os
import time
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
SIN_RIF = "cli_sin_rif"
T0 = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
TEST_PWD = "TestAudit2026*Xy"
TEST_PWD2 = "TestAudit2026*Zw"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def _rawdb():
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def H():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=30)
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"admin login failed {r.status_code} {r.text[:200]}")
    return {"Authorization": "Bearer " + r.json()["session_token"]}


def trails(H, **params):
    params.setdefault("date_from", T0)
    params.setdefault("page_size", 200)
    r = requests.get(f"{BASE_URL}/api/audit-trails", headers=H, params=params, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def detail(H, tid):
    r = requests.get(f"{BASE_URL}/api/audit-trails/{tid}", headers=H, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


# ---------- API básica ----------
class TestApiBasics:
    def test_filters(self, H):
        r = requests.get(f"{BASE_URL}/api/audit-trails/filters", headers=H, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "Cotizaciones" in d["modules"] and "Bancos" in d["modules"]
        assert d["actions"] == ["CREATE", "UPDATE", "DELETE"]
        assert isinstance(d["users"], list) and len(d["users"]) > 0
        assert "Proyectos" not in d["modules"]

    def test_list_structure_pagination(self, H):
        r = requests.get(f"{BASE_URL}/api/audit-trails", headers=H, timeout=30)
        d = r.json()
        assert r.status_code == 200 and d["page_size"] == 50 and d["page"] == 1
        assert d["total_all"] >= d["total"]
        for it in d["items"]:
            assert "valores_anteriores" not in it and "id" in it

    def test_no_put_delete(self, H):
        d = requests.get(f"{BASE_URL}/api/audit-trails?page_size=1", headers=H, timeout=30).json()
        tid = d["items"][0]["id"] if d["items"] else "000000000000000000000000"
        for m in ("put", "delete", "patch"):
            r = getattr(requests, m)(f"{BASE_URL}/api/audit-trails/{tid}", headers=H, json={}, timeout=30)
            assert r.status_code in (404, 405), f"{m} -> {r.status_code}"
        r = requests.post(f"{BASE_URL}/api/audit-trails", headers=H, json={}, timeout=30)
        assert r.status_code in (404, 405)

    def test_detail_404(self, H):
        assert requests.get(f"{BASE_URL}/api/audit-trails/xyz", headers=H, timeout=30).status_code == 404
        assert requests.get(f"{BASE_URL}/api/audit-trails/000000000000000000000000", headers=H, timeout=30).status_code == 404

    def test_bad_date_400(self, H):
        r = requests.get(f"{BASE_URL}/api/audit-trails?date_from=notadate", headers=H, timeout=30)
        assert r.status_code == 400

    def test_unauth_401(self):
        r = requests.get(f"{BASE_URL}/api/audit-trails", timeout=30)
        assert r.status_code in (401, 403)


# ---------- Cotizaciones PRE → CREATE / UPDATE(assign) / DELETE ----------
class TestQuotesFlow:
    state = {}

    def test_create_pre_quote(self, H):
        payload = {
            "client_id": SIN_RIF, "quote_category": "implementation", "quote_type": "VPOS",
            "services": [{"item_id": f"svc_{uuid.uuid4().hex[:8]}", "item_name": "TEST_ITER364_svc", "item_type": "setup",
                          "unit_price_usd": 100.0, "quantity": 1, "total_usd": 100.0, "cantidad_cajas": 1, "cantidad_bancos": 1}],
            "hardware": [], "equipment_items": [], "cantidad_cajas": 1, "cantidad_bancos": 1,
            "notes": "TEST_ITER364", "client_segment": "PYME",
        }
        r = requests.post(f"{BASE_URL}/api/quotes", headers=H, json=payload, timeout=60)
        assert r.status_code in (200, 201), r.text[:300]
        q = r.json()
        self.state.update(qid=q["quote_id"], num=q["quote_number"])
        assert q["quote_number"].startswith("PRE-")
        time.sleep(0.5)
        d = trails(H, registro=q["quote_number"], action="CREATE", modules="Cotizaciones")
        assert d["total"] >= 1, d
        t = detail(H, d["items"][0]["id"])
        assert t["modulo"] == "Cotizaciones" and t["entidad"] == "quotes"
        assert t["registro_id"] == q["quote_number"]
        assert t["valores_anteriores"] is None
        assert t["valores_nuevos"]["quote_id"] == q["quote_id"] and t["valores_nuevos"]["notes"] == "TEST_ITER364"
        assert t["usuario_email"] == ADMIN["email"]
        assert t["endpoint"] == "POST /api/quotes"
        assert t["ip_origen"] and t["user_agent"]

    def test_assign_client_update(self, H):
        if not self.state.get("qid"):
            pytest.skip("no quote")
        cl = requests.get(f"{BASE_URL}/api/clients", headers=H, timeout=30).json()
        real = next(c for c in cl if c.get("rif") and not c.get("is_placeholder") and c["client_id"] != SIN_RIF)
        r = requests.post(f"{BASE_URL}/api/quotes/{self.state['qid']}/assign-client", headers=H,
                          json={"client_id": real["client_id"]}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        new_num = r.json()["quote_number"]
        self.state["num2"] = new_num
        time.sleep(0.5)
        d = trails(H, registro=self.state["qid"], action="UPDATE")
        found = None
        for it in d["items"]:
            if "client_id" in it["campos_modificados"] and "quote_number" in it["campos_modificados"]:
                found = detail(H, it["id"])
        assert found, [i["campos_modificados"] for i in d["items"]]
        assert found["valores_anteriores"]["quote_number"] == self.state["num"]
        assert found["valores_nuevos"]["quote_number"] == new_num
        assert found["valores_anteriores"]["client_id"] == SIN_RIF
        assert "updated_at" not in found["campos_modificados"]

    def test_combined_filters(self, H):
        d = trails(H, modules="Cotizaciones", action="UPDATE")
        assert d["total"] >= 1
        assert all(i["modulo"] == "Cotizaciones" and i["accion"] == "UPDATE" for i in d["items"])
        p1 = trails(H, page_size=1, page=1)
        p2 = trails(H, page_size=1, page=2)
        if p1["total"] >= 2:
            assert p1["items"][0]["id"] != p2["items"][0]["id"]
        d = trails(H, field="quote_number", registro=self.state.get("qid", "x"))
        assert all(any("quote_number" in c for c in i["campos_modificados"]) for i in d["items"])

    def test_delete_quote(self, H):
        if not self.state.get("qid"):
            pytest.skip("no quote")
        r = requests.delete(f"{BASE_URL}/api/quotes/{self.state['qid']}", headers=H, timeout=30)
        assert r.status_code == 200
        time.sleep(0.5)
        d = trails(H, registro=self.state["qid"], action="DELETE", modules="Cotizaciones")
        assert d["total"] >= 1
        t = detail(H, d["items"][0]["id"])
        assert t["valores_nuevos"] is None and t["valores_anteriores"]["quote_id"] == self.state["qid"]
        assert t["campos_modificados"] is None

    def test_export_xlsx(self, H):
        r = requests.get(f"{BASE_URL}/api/audit-trails/export", headers=H,
                         params={"date_from": T0, "modules": "Cotizaciones"}, timeout=60)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0][0].startswith("Fecha")
        assert len(rows) >= 4
        assert all(r[1] == "Cotizaciones" for r in rows[1:])


# ---------- Política de seguridad / banco / cliente ----------
class TestUpdates:
    def test_security_policy_update_and_noop(self, H):
        pol = requests.get(f"{BASE_URL}/api/admin/security-policy", headers=H, timeout=30).json()
        orig = pol.get("lockout_minutes") or 15
        new = dict(pol, lockout_minutes=orig + 1)
        r = requests.put(f"{BASE_URL}/api/admin/security-policy", headers=H, json=new, timeout=30)
        assert r.status_code == 200, r.text[:300]
        try:
            time.sleep(0.5)
            d = trails(H, modules="Usuarios y Seguridad", action="UPDATE", field="lockout_minutes")
            assert d["total"] >= 1
            t = detail(H, d["items"][0]["id"])
            assert t["campos_modificados"] == ["lockout_minutes"], t["campos_modificados"]
            assert t["valores_anteriores"]["lockout_minutes"] == orig
            assert t["valores_nuevos"]["lockout_minutes"] == orig + 1
            # PUT idéntico → sin nueva pista
            before = trails(H, modules="Usuarios y Seguridad")["total"]
            requests.put(f"{BASE_URL}/api/admin/security-policy", headers=H, json=new, timeout=30)
            time.sleep(0.5)
            after = trails(H, modules="Usuarios y Seguridad")["total"]
            assert after == before, f"no-op PUT generated {after - before} trails"
        finally:
            requests.put(f"{BASE_URL}/api/admin/security-policy", headers=H, json=dict(pol, lockout_minutes=orig), timeout=30)

    def test_bank_integration_notes(self, H):
        banks = requests.get(f"{BASE_URL}/api/banks", headers=H, timeout=30).json()
        bank = banks[0]
        r = requests.post(f"{BASE_URL}/api/banks/{bank['bank_id']}/integrations", headers=H,
                          json={"service_name": "TEST_ITER364_svc", "component_type": "VPOS/MPOS", "notes": "orig"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        iid = r.json()["integration_id"]
        url = f"{BASE_URL}/api/banks/{bank['bank_id']}/integrations/{iid}"
        try:
            time.sleep(0.5)
            d0 = trails(H, modules="Bancos", action="UPDATE", registro=bank["bank_id"])
            assert d0["total"] >= 1, "push integration not audited"
            r = requests.put(url, headers=H, json={"notes": "TEST_ITER364_note"}, timeout=30)
            assert r.status_code == 200, r.text[:300]
            time.sleep(0.5)
            d = trails(H, modules="Bancos", action="UPDATE", registro=bank["bank_id"])
            assert d["total"] == d0["total"] + 1
            t = detail(H, d["items"][0]["id"])
            key = f"integrations[{iid}].notes"
            assert t["campos_modificados"] == [key], t["campos_modificados"]
            assert t["valores_nuevos"][key] == "TEST_ITER364_note"
            assert t["valores_anteriores"][key] == "orig"
            n = d["total"]
            requests.put(url, headers=H, json={"notes": "TEST_ITER364_note"}, timeout=30)
            time.sleep(0.5)
            assert trails(H, modules="Bancos", action="UPDATE", registro=bank["bank_id"])["total"] == n, "no-op PUT generated trail"
        finally:
            rd = requests.delete(url, headers=H, timeout=30)
            assert rd.status_code == 200

    def test_client_crud(self, H):
        rif = f"J{uuid.uuid4().int % 10**9:09d}"
        body = {"rif": rif, "legal_name": "TEST_ITER364 CA", "fantasy_name": "TEST_ITER364"}
        r = requests.post(f"{BASE_URL}/api/clients", headers=H, json=body, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        cid = r.json().get("client_id")
        try:
            r = requests.put(f"{BASE_URL}/api/clients/{cid}", headers=H, json=dict(body, fantasy_name="TEST_ITER364_upd"), timeout=30)
            assert r.status_code == 200, r.text[:300]
        finally:
            rd = requests.delete(f"{BASE_URL}/api/clients/{cid}", headers=H, timeout=30)
        assert rd.status_code == 200
        time.sleep(0.5)
        d = trails(H, registro=cid, modules="Clientes")
        acts = {i["accion"] for i in d["items"]}
        assert {"CREATE", "UPDATE", "DELETE"} <= acts, acts
        upd = [i for i in d["items"] if i["accion"] == "UPDATE"]
        assert any("fantasy_name" in i["campos_modificados"] for i in upd)


# ---------- Aislamiento Proyectos ----------
class TestProjectsIsolation:
    def test_project_change_no_trail(self, H):
        projs = requests.get(f"{BASE_URL}/api/projects", headers=H, timeout=60).json()
        projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
        if not projs:
            pytest.skip("no projects")
        p = projs[0]
        orig = p.get("priority") or "Normal"
        other = "Alta" if orig != "Alta" else "Normal"
        before = trails(H)["total"]
        r = requests.put(f"{BASE_URL}/api/projects/{p['project_id']}/priority", headers=H, json={"priority": other}, timeout=30)
        requests.put(f"{BASE_URL}/api/projects/{p['project_id']}/priority", headers=H, json={"priority": orig}, timeout=30)
        time.sleep(0.5)
        assert r.status_code in (200, 400), r.text[:200]
        d = trails(H)
        new_items = [i for i in d["items"] if "/api/projects" in (i.get("endpoint") or "")]
        assert not new_items, new_items
        assert d["total"] == before, f"projects op produced {d['total'] - before} trails (could be concurrent noise)"


# ---------- RBAC + login + password ----------
class TestRbacAndPassword:
    st = {}

    @classmethod
    def setup_class(cls):
        uid = f"user_test364_{uuid.uuid4().hex[:8]}"
        email = f"test_iter364_{uuid.uuid4().hex[:6]}@example.com"
        import hashlib, secrets
        def hash_password(p):
            salt = secrets.token_hex(16)
            return f"{salt}:{hashlib.sha256((p + salt).encode()).hexdigest()}"
        now = datetime.now(timezone.utc).isoformat()
        doc = {"user_id": uid, "email": email, "first_name": "TEST_ITER364", "last_name": "Auditor", "name": "TEST_ITER364 Auditor",
               "role": "user", "is_active": True, "password_hash": hash_password(TEST_PWD), "must_change_password": False,
               "password_changed_at": now, "password_history": [], "special_permissions": [], "permissions": {},
               "created_at": now, "email_verified": True,
               "menu_groups": {"dashboard": True, "gestion_comercial": True}}
        _rawdb().users.insert_one(doc)
        cls.st.update(uid=uid, email=email)

    @classmethod
    def teardown_class(cls):
        _rawdb().users.delete_one({"user_id": cls.st["uid"]})

    def _login(self, pwd):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": self.st["email"], "password": pwd}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("session_token"), r.json()
        return {"Authorization": "Bearer " + r.json()["session_token"]}

    def test_login_no_trail(self, H):
        uh = self._login(TEST_PWD)
        self.st["uh"] = uh
        time.sleep(0.5)
        d = trails(H, registro=self.st["email"])
        d2 = trails(H, registro=self.st["uid"])
        assert d["total"] == 0 and d2["total"] == 0, [i["campos_modificados"] for i in d["items"] + d2["items"]]

    def test_forbidden_then_granted(self, H):
        uh = self.st.get("uh") or self._login(TEST_PWD)
        assert requests.get(f"{BASE_URL}/api/audit-trails", headers=uh, timeout=30).status_code == 403
        assert requests.get(f"{BASE_URL}/api/audit-trails/filters", headers=uh, timeout=30).status_code == 403
        assert requests.get(f"{BASE_URL}/api/audit-trails/export", headers=uh, timeout=30).status_code == 403
        r = requests.put(f"{BASE_URL}/api/admin/users/{self.st['uid']}/special-permissions", headers=H,
                         json={"special_permissions": ["configuracion:auditor"]}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert requests.get(f"{BASE_URL}/api/audit-trails", headers=uh, timeout=30).status_code == 200
        time.sleep(0.5)
        d = trails(H, registro=self.st["email"], action="UPDATE", field="special_permissions")
        assert d["total"] >= 1
        r = requests.put(f"{BASE_URL}/api/admin/users/{self.st['uid']}/special-permissions", headers=H,
                         json={"special_permissions": []}, timeout=30)
        assert r.status_code == 200
        assert requests.get(f"{BASE_URL}/api/audit-trails", headers=uh, timeout=30).status_code == 403

    def test_change_password_masked(self, H):
        uh = self.st.get("uh") or self._login(TEST_PWD)
        r = requests.post(f"{BASE_URL}/api/auth/change-password", headers=uh,
                          json={"current_password": TEST_PWD, "new_password": TEST_PWD2}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        time.sleep(0.5)
        d = trails(H, registro=self.st["email"], action="UPDATE", field="password_hash")
        assert d["total"] >= 1, d
        t = detail(H, d["items"][0]["id"])
        assert t["valores_anteriores"]["password_hash"] == "***"
        assert t["valores_nuevos"]["password_hash"] == "***"
        import json as _j
        blob = _j.dumps(t)
        assert ":" not in str(t["valores_nuevos"].get("password_hash"))
        for k, v in (t["valores_nuevos"] or {}).items():
            if "password" in k or "hash" in k:
                assert v == "***", (k, v)
