# Iter407: Cierre Administrativo (all quotes) + Admin reassign Referente of Initial Contacts
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = ("qa.integradores@megasoft.com.ve", "QaIntegr2026*Ok")
NON_ADMIN = ("test_iter407_user@example.com", "TestIter407*Pwd!")
CLIENT_ID = "cli_05f6268761c7"

_state = {"quotes": [], "contacts": []}


def _login(email, pwd):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {email}: {r.status_code} {r.text[:150]}")
    return {"Authorization": f"Bearer {r.json()['session_token']}"}


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def user():
    return _login(*NON_ADMIN)


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    h = _login(*ADMIN)
    for qid in _state["quotes"]:
        requests.delete(f"{BASE_URL}/api/quote-history/qhist_{qid}", headers=h, timeout=30)
        requests.delete(f"{BASE_URL}/api/quotes/{qid}", headers=h, timeout=30)
    for cid in _state["contacts"]:
        requests.delete(f"{BASE_URL}/api/initial-contacts/{cid}", headers=h, timeout=30)


def _create_quote(h, category="implementation"):
    payload = {"client_id": CLIENT_ID, "quote_category": category, "quote_type": "VPOS",
               "notes": "TEST_iter407 admin close"}
    r = requests.post(f"{BASE_URL}/api/quotes", json=payload, headers=h, timeout=30)
    assert r.status_code == 200, r.text
    q = r.json()
    _state["quotes"].append(q["quote_id"])
    return q


# ---------- Referente reassignment ----------
class TestReferente:
    def test_reassign_flow(self, admin, user):
        refs = requests.get(f"{BASE_URL}/api/referentes", headers=admin, timeout=30)
        assert refs.status_code == 200, refs.text
        data = refs.json()
        items = data if isinstance(data, list) else (data.get("items") or data.get("referentes") or [])
        assert len(items) >= 2
        r1, r2 = items[0], items[1]
        c = requests.post(f"{BASE_URL}/api/initial-contacts", headers=admin, timeout=30, json={
            "contact_name": "TEST_iter407 Contacto", "legal_name": "TEST_iter407 CA",
            "referente_id": r1["referente_id"], "email": "test_iter407@example.com"})
        assert c.status_code == 200, c.text
        cid = c.json()["contact_id"]
        _state["contacts"].append(cid)
        assert c.json().get("referente_id") == r1["referente_id"]

        url = f"{BASE_URL}/api/initial-contacts/{cid}/referente"
        # non-admin 403
        r = requests.put(url, headers=user, json={"referente_id": r2["referente_id"]}, timeout=30)
        assert r.status_code == 403, r.text
        # same 400
        r = requests.put(url, headers=admin, json={"referente_id": r1["referente_id"]}, timeout=30)
        assert r.status_code == 400, r.text
        # unknown 400
        r = requests.put(url, headers=admin, json={"referente_id": "ref_nope_000"}, timeout=30)
        assert r.status_code == 400, r.text
        # 404 contact
        r = requests.put(f"{BASE_URL}/api/initial-contacts/ic_nope000/referente", headers=admin,
                         json={"referente_id": r2["referente_id"]}, timeout=30)
        assert r.status_code == 404
        # OK
        r = requests.put(url, headers=admin, json={"referente_id": r2["referente_id"], "comment": "TEST consolidar"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["referente_id"] == r2["referente_id"]
        assert d["referred_by"] == r2["nombre_referente"]
        last = d["bitacora"][-1]
        assert last["action"] == "referente_reassigned"
        assert "TEST consolidar" in last["description"]
        # persisted
        g = requests.get(f"{BASE_URL}/api/initial-contacts/{cid}", headers=admin, timeout=30)
        if g.status_code == 200:
            assert g.json()["referente_id"] == r2["referente_id"]


# ---------- Admin close ----------
class TestAdminClose:
    def test_catalog(self, admin):
        r = requests.get(f"{BASE_URL}/api/action-notifications/catalog", headers=admin, timeout=30)
        assert r.status_code == 200, r.text
        txt = r.text
        assert "admin_close" in txt and "Cierre Administrativo" in txt

    def test_non_admin_forbidden(self, admin, user):
        q = _create_quote(admin)
        r = requests.get(f"{BASE_URL}/api/quotes/{q['quote_id']}/admin-close/check", headers=user, timeout=30)
        assert r.status_code == 403, r.text
        r = requests.post(f"{BASE_URL}/api/quotes/{q['quote_id']}/admin-close", headers=user,
                          data={"reason": "TEST motivo suficientemente largo"}, timeout=30)
        assert r.status_code == 403, r.text

    def test_admin_close_flow(self, admin):
        q = _create_quote(admin)
        qid = q["quote_id"]
        r = requests.get(f"{BASE_URL}/api/quotes/{qid}/admin-close/check", headers=admin, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["eligible"] is True
        r = requests.post(f"{BASE_URL}/api/quotes/{qid}/admin-close", headers=admin, data={"reason": "corto"}, timeout=30)
        assert r.status_code == 400
        r = requests.post(f"{BASE_URL}/api/quotes/{qid}/admin-close", headers=admin,
                          data={"reason": "TEST_iter407 cierre administrativo de prueba"}, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["quote_status"] == "Cierre Administrativo"
        # not in active list
        lst = requests.get(f"{BASE_URL}/api/quotes", headers=admin, timeout=60)
        assert lst.status_code == 200
        assert qid not in [x["quote_id"] for x in lst.json()]
        # in history
        h = requests.get(f"{BASE_URL}/api/quote-history/qhist_{qid}", headers=admin, timeout=30)
        assert h.status_code == 200, h.text
        hd = h.json()
        hd = hd.get("history", hd) if isinstance(hd, dict) else hd
        assert hd["quote_status_final"] == "Cierre Administrativo"
        assert hd["admin_closure"]["reason"] == "TEST_iter407 cierre administrativo de prueba"
        hl = requests.get(f"{BASE_URL}/api/quote-history", headers=admin, params={"search": q["quote_number"]}, timeout=60)
        assert hl.status_code == 200
        assert qid in hl.text
        # check now not eligible, second call 400
        r = requests.get(f"{BASE_URL}/api/quotes/{qid}/admin-close/check", headers=admin, timeout=30)
        assert r.json()["eligible"] is False
        r = requests.post(f"{BASE_URL}/api/quotes/{qid}/admin-close", headers=admin,
                          data={"reason": "TEST second call long enough"}, timeout=30)
        assert r.status_code == 400

    def test_bad_attachment_rejected(self, admin):
        q = _create_quote(admin)
        r = requests.post(f"{BASE_URL}/api/quotes/{q['quote_id']}/admin-close", headers=admin,
                          data={"reason": "TEST motivo suficientemente largo"},
                          files={"file": ("x.exe", b"MZ", "application/octet-stream")}, timeout=30)
        assert r.status_code == 400
        chk = requests.get(f"{BASE_URL}/api/quotes/{q['quote_id']}/admin-close/check", headers=admin, timeout=30)
        assert chk.json()["eligible"] is True

    def test_404(self, admin):
        r = requests.get(f"{BASE_URL}/api/quotes/quo_nope000/admin-close/check", headers=admin, timeout=30)
        assert r.status_code == 404


# ---------- Override authorizes non-admin ----------
class TestOverride:
    def test_override_allows_user(self, admin, user):
        key = "implementacion_pyme|vpos|admin_close"
        q = _create_quote(admin)
        try:
            r = requests.put(f"{BASE_URL}/api/quote-action-overrides", headers=admin, timeout=30, json={
                "business_type": "implementacion_pyme", "product_subcategory": "vpos", "action_id": "admin_close",
                "custom_label": "TEST Cierre Adm", "enabled": True, "allowed_user_ids": ["user_test_iter407"]})
            assert r.status_code == 200, r.text
            assert r.json()["config_key"] == key
            c = requests.get(f"{BASE_URL}/api/quotes/{q['quote_id']}/admin-close/check", headers=user, timeout=30)
            assert c.status_code == 200, c.text
            assert c.json()["eligible"] is True
            # disabled override -> user denied
            requests.put(f"{BASE_URL}/api/quote-action-overrides", headers=admin, timeout=30, json={
                "business_type": "implementacion_pyme", "product_subcategory": "vpos", "action_id": "admin_close",
                "enabled": False, "allowed_user_ids": ["user_test_iter407"]})
            c = requests.get(f"{BASE_URL}/api/quotes/{q['quote_id']}/admin-close/check", headers=user, timeout=30)
            assert c.status_code == 403
        finally:
            requests.delete(f"{BASE_URL}/api/quote-action-overrides/{key.replace('|', '%7C')}", headers=admin, timeout=30)
