"""iter340 — Comunicación Masiva: A Integradores (regresión _mass_dispatch) + A Bancos/Entes (nuevo).

Usa SOLO fixtures (bnk_TEST_* / int_TEST_* con correos @example.com). Limpieza por ids / ventana de tiempo.
"""
import os
import io
import json
import uuid
import asyncio
from datetime import datetime, timezone
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env", override=False)

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/') + '/api'
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "admin123"}
NON_ADMIN = {"email": "jrojas@megasoft.com.ve", "password": "Test1234!"}
START = datetime.now(timezone.utc).isoformat()
SUF = uuid.uuid4().hex[:6]
BANK1 = f"bnk_TEST_{SUF}a"
BANK2 = f"bnk_TEST_{SUF}b"
BANK3 = f"bnk_TEST_{SUF}c"  # legacy contact_* fields
INT1 = f"int_TEST_{SUF}a"
INT2 = f"int_TEST_{SUF}b"
ACTIONS = ["bank_mass_communication", "integrator_mass_communication"]


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _db_op(fn):
    c = AsyncIOMotorClient(MONGO_URL)
    try:
        return await fn(c[DB_NAME])
    finally:
        c.close()


@pytest.fixture(scope="module")
def H():
    r = requests.post(f"{BASE_URL}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    t = r.json().get("session_token") or r.json().get("token")
    return {"Authorization": f"Bearer {t}"}


TPL_ID = f"tpl_TEST_{SUF}"


@pytest.fixture(scope="module")
def tpl(H):
    r = requests.get(f"{BASE_URL}/email-templates?context=INTEGRADORES", headers=H, timeout=30)
    assert r.status_code == 200
    found = [t for t in r.json() if t["template_id"] == TPL_ID]
    assert found, "fixture template not listed under INTEGRADORES"
    return found[0]


@pytest.fixture(scope="module", autouse=True)
def fixtures():
    banks = [
        {"bank_id": BANK1, "name": f"TEST_BANCO_A_{SUF}", "contacts": [
            {"full_name": "TEST Ana", "email": f"ana_{SUF}@example.com", "position": "Gerente"},
            {"full_name": "TEST Beto", "email": f"beto_{SUF}@example.com", "position": "Analista"},
            {"full_name": "TEST Ceci", "email": f"ceci_{SUF}@example.com", "position": "Jefe"},
            {"full_name": "TEST Dup", "email": f"ANA_{SUF}@example.com", "position": "Dup"},
            {"full_name": "TEST NoMail", "email": "", "position": "Sin"},
        ]},
        {"bank_id": BANK2, "name": f"TEST_BANCO_B_{SUF}", "contacts": [
            {"first_name": "TEST", "last_name": "Eva", "email": f"eva_{SUF}@example.com", "position": "Dir"},
        ]},
        {"bank_id": BANK3, "name": f"TEST_BANCO_C_{SUF}", "contact_name": "TEST Legacy Lu",
         "contact_email": f"lu_{SUF}@example.com"},
    ]
    ints = [
        {"integrator_id": INT1, "name": f"TEST_INT_A_{SUF}", "email": f"inta_{SUF}@example.com", "integration_type": "PG", "contacts": []},
        {"integrator_id": INT2, "name": f"TEST_INT_B_{SUF}", "email": "", "integration_type": "PG", "contacts": []},
    ]

    async def setup(db):
        await db.banks.insert_many([dict(b) for b in banks])
        await db.integrators.insert_many([dict(i) for i in ints])
        await db.email_templates.insert_one({"template_id": TPL_ID, "context": "INTEGRADORES", "name": f"TEST_TPL_{SUF}",
                                             "subject": "TEST Comunicado {{fecha_sistema}}", "body_html": "<p><b>TEST</b> body</p>"})
    _run(_db_op(setup))
    yield

    async def teardown(db):
        await db.banks.delete_many({"bank_id": {"$in": [BANK1, BANK2, BANK3]}})
        await db.integrators.delete_many({"integrator_id": {"$in": [INT1, INT2]}})
        await db.email_templates.delete_one({"template_id": TPL_ID})
        await db.bitacora.delete_many({"action": "bank_mass_communication", "bank_ids": {"$elemMatch": {"$in": [BANK1, BANK2, BANK3]}}})
        await db.bitacora.delete_many({"action": {"$in": ACTIONS}, "template_id": TPL_ID})
        await db.email_logs.delete_many({"action": {"$in": ACTIONS}, "created_at": {"$gte": START},
                                         "subject": {"$regex": "^TEST Comunicado"}})
    _run(_db_op(teardown))


def _send_bank(H, keys, template_id, docs="[]", files=None):
    return requests.post(f"{BASE_URL}/banks/mass/communication", headers=H, files=files,
                         data={"template_id": template_id, "contact_keys": json.dumps(keys), "internal_doc_ids": docs}, timeout=60)


# --- Regresión: A Integradores ---
class TestIntegratorsRegression:
    def test_send_shape(self, H, tpl):
        r = requests.post(f"{BASE_URL}/integrators/mass/communication", headers=H,
                          data={"template_id": tpl["template_id"], "integrator_ids": json.dumps([INT1, INT2])}, timeout=60)
        assert r.status_code == 200, r.text
        b = r.json()
        assert set(["status", "recipients_count", "attachments_count", "subject", "message"]).issubset(b)
        assert b["recipients_count"] == 1 and b["attachments_count"] == 0
        assert "1 integrador(es)" in b["message"]
        assert isinstance(b["subject"], str) and b["subject"]

    def test_empty_ids_400(self, H, tpl):
        r = requests.post(f"{BASE_URL}/integrators/mass/communication", headers=H,
                          data={"template_id": tpl["template_id"], "integrator_ids": "[]"}, timeout=30)
        assert r.status_code == 400

    def test_bad_template_404(self, H):
        r = requests.post(f"{BASE_URL}/integrators/mass/communication", headers=H,
                          data={"template_id": "tpl_nope_xx", "integrator_ids": json.dumps([INT1])}, timeout=30)
        assert r.status_code == 404

    def test_no_email_400(self, H, tpl):
        r = requests.post(f"{BASE_URL}/integrators/mass/communication", headers=H,
                          data={"template_id": tpl["template_id"], "integrator_ids": json.dumps([INT2])}, timeout=30)
        assert r.status_code == 400


# --- Bancos/Entes: GET recipients ---
class TestBankRecipients:
    def test_structure_and_fixtures(self, H):
        r = requests.get(f"{BASE_URL}/banks/mass/recipients", headers=H, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert {"banks", "total_contacts", "with_email"}.issubset(d)
        by = {b["bank_id"]: b for b in d["banks"]}
        assert BANK1 in by and BANK2 in by and BANK3 in by
        c = by[BANK1]["contacts"]
        assert len(c) == 5
        assert set(c[0]) == {"key", "name", "email", "position", "has_email"}
        assert c[0]["key"] == f"{BANK1}::0" and c[0]["name"] == "TEST Ana" and c[0]["position"] == "Gerente"
        assert c[4]["has_email"] is False
        assert by[BANK2]["contacts"][0]["name"] == "TEST Eva"
        assert by[BANK3]["contacts"][0]["email"] == f"lu_{SUF}@example.com"

    def test_forbidden_non_admin(self):
        r = requests.post(f"{BASE_URL}/auth/login", json=NON_ADMIN, timeout=30)
        if r.status_code != 200:
            pytest.skip("non-admin login fail")
        t = r.json().get("session_token") or r.json().get("token")
        r2 = requests.get(f"{BASE_URL}/banks/mass/recipients", headers={"Authorization": f"Bearer {t}"}, timeout=30)
        assert r2.status_code == 403


# --- Bancos/Entes: POST communication ---
class TestBankSend:
    def test_only_selected_dedup_and_bitacora(self, H, tpl):
        keys = [f"{BANK1}::0", f"{BANK1}::3", f"{BANK1}::4", f"{BANK2}::0", f"{BANK3}::0"]  # Beto/Ceci deselected
        r = _send_bank(H, keys, tpl["template_id"])
        assert r.status_code == 200, r.text
        b = r.json()
        rec = [e.lower() for e in b["recipients"]]
        assert rec == [f"ana_{SUF}@example.com", f"eva_{SUF}@example.com", f"lu_{SUF}@example.com"] or \
            sorted(rec) == sorted([f"ana_{SUF}@example.com", f"eva_{SUF}@example.com", f"lu_{SUF}@example.com"])
        assert f"beto_{SUF}@example.com" not in rec and f"ceci_{SUF}@example.com" not in rec
        assert b["recipients_count"] == 3 and b["banks_count"] == 3
        assert b["attachments_count"] == 0

        async def q(db):
            return await db.bitacora.find_one({"action": "bank_mass_communication", "bank_ids": BANK2}, {"_id": 0})
        log = _run(_db_op(q))
        assert log and log["recipients_count"] == 3
        assert sorted(e.lower() for e in log["recipients"]) == sorted(rec)

    def test_unknown_keys_ignored(self, H, tpl):
        r = _send_bank(H, [f"{BANK2}::0", f"{BANK2}::9", "bnk_doesnotexist::0"], tpl["template_id"])
        assert r.status_code == 200, r.text
        assert r.json()["recipients"] == [f"eva_{SUF}@example.com"]

    def test_with_local_attachment(self, H, tpl):
        files = [("files", ("TEST_local.txt", io.BytesIO(b"hola"), "text/plain"))]
        r = _send_bank(H, [f"{BANK2}::0"], tpl["template_id"], files=files)
        assert r.status_code == 200, r.text
        assert r.json()["attachments_count"] == 1

    def test_empty_400(self, H, tpl):
        assert _send_bank(H, [], tpl["template_id"]).status_code == 400

    def test_invalid_json_400(self, H, tpl):
        r = requests.post(f"{BASE_URL}/banks/mass/communication", headers=H,
                          data={"template_id": tpl["template_id"], "contact_keys": "notjson"}, timeout=30)
        assert r.status_code == 400

    def test_no_valid_email_400(self, H, tpl):
        assert _send_bank(H, [f"{BANK1}::4"], tpl["template_id"]).status_code == 400

    def test_bad_template_404(self, H):
        assert _send_bank(H, [f"{BANK2}::0"], "tpl_nope_xx").status_code == 404

    def test_missing_doc_422(self, H, tpl):
        r = _send_bank(H, [f"{BANK2}::0"], tpl["template_id"], docs=json.dumps(["edoc_NOPE"]))
        assert r.status_code == 422
