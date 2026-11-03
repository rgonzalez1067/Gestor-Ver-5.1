"""iter343 — Variables Banco/Contacto en plantillas INTEGRADORES + modo de envío automático
(per_contact / per_bank / single_bcc) en POST /api/banks/mass/communication. Solo fixtures TEST_."""
import os
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
START = datetime.now(timezone.utc).isoformat()
SUF = uuid.uuid4().hex[:6]
B1, B2 = f"bnk_TEST_{SUF}a", f"bnk_TEST_{SUF}b"
T_CONTACT, T_BANK, T_NONE, T_DOUBLE = (f"tpl_TEST_{SUF}_{x}" for x in ("c", "b", "n", "d"))
ALL_TPL = [T_CONTACT, T_BANK, T_NONE, T_DOUBLE]


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


@pytest.fixture(scope="module", autouse=True)
def fixtures():
    banks = [
        {"bank_id": B1, "name": f"TEST_BANCO_A_{SUF}", "rif": "J-111", "bank_code": "0991", "type": "Banco",
         "country": "Venezuela", "procesador": "PROC_A", "contacts": [
            {"full_name": "TEST Ana", "email": f"ana_{SUF}@example.com", "position": "Gerente", "phone": "0412-1"},
            {"full_name": "TEST Beto", "email": f"beto_{SUF}@example.com", "position": "Analista", "phone": "0412-2"},
            {"full_name": "TEST Ceci", "email": f"ceci_{SUF}@example.com", "position": "Jefe", "phone": "0412-3"},
        ]},
        {"bank_id": B2, "name": f"TEST_BANCO_B_{SUF}", "rif": "J-222", "bank_code": "0992", "type": "Ente",
         "country": "Panama", "procesador": "PROC_B", "contacts": [
            {"full_name": "TEST Eva", "email": f"eva_{SUF}@example.com", "position": "Dir", "phone": "0414-9"},
        ]},
    ]
    tpls = [
        {"template_id": T_CONTACT, "subject": f"TEST343 {SUF} Hola {{contacto_nombre}} de {{banco_nombre}}",
         "body_html": "<p>Estimado {contacto_nombre} ({contacto_cargo}) {contacto_email} {contacto_telefono} - {banco_rif} {banco_codigo}</p>"},
        {"template_id": T_BANK, "subject": f"TEST343 {SUF} Aviso a {{banco_nombre}}",
         "body_html": "<p>{banco_nombre} RIF {banco_rif} tipo {banco_tipo} pais {banco_pais} proc {banco_procesador}</p>"},
        {"template_id": T_NONE, "subject": f"TEST343 {SUF} General", "body_html": "<p>Sin variables</p>"},
        {"template_id": T_DOUBLE, "subject": f"TEST343 {SUF} D {{{{banco_nombre}}}}", "body_html": "<p>x</p>"},
    ]

    async def setup(db):
        await db.banks.insert_many([dict(b) for b in banks])
        await db.email_templates.insert_many([{**t, "context": "INTEGRADORES", "name": f"TEST_{t['template_id']}"} for t in tpls])
    _run(_db_op(setup))
    yield

    async def teardown(db):
        await db.banks.delete_many({"bank_id": {"$in": [B1, B2]}})
        await db.email_templates.delete_many({"template_id": {"$in": ALL_TPL}})
        await db.bitacora.delete_many({"action": "bank_mass_communication", "template_id": {"$in": ALL_TPL}})
        await db.email_logs.delete_many({"action": "bank_mass_communication", "created_at": {"$gte": START},
                                         "subject": {"$regex": f"^TEST343 {SUF}"}})
    _run(_db_op(teardown))


def _send(H, keys, tid):
    return requests.post(f"{BASE_URL}/banks/mass/communication", headers=H,
                         data={"template_id": tid, "contact_keys": json.dumps(keys)}, timeout=90)


def _logs():
    async def q(db):
        return [d async for d in db.email_logs.find(
            {"action": "bank_mass_communication", "subject": {"$regex": f"^TEST343 {SUF}"}}, {"_id": 0})]
    return _run(_db_op(q))


SEL = [f"{B1}::idx0", f"{B1}::idx2", f"{B2}::idx0"]  # Beto (idx1) deselected


class TestSendMode:
    def test_recipients_keys_include_phone(self, H):
        r = requests.get(f"{BASE_URL}/banks/mass/recipients", headers=H, timeout=60)
        assert r.status_code == 200
        by = {b["bank_id"]: b for b in r.json()["banks"]}
        keys = [c["key"] for c in by[B1]["contacts"]]
        assert keys == [f"{B1}::idx0", f"{B1}::idx1", f"{B1}::idx2"]
        assert by[B1]["contacts"][0]["phone"] == "0412-1"

    def test_per_contact(self, H):
        r = _send(H, SEL, T_CONTACT)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["send_mode"] == "per_contact"
        assert b["batches_count"] == 3 and b["recipients_count"] == 3 and b["banks_count"] == 2
        assert f"beto_{SUF}@example.com" not in b["recipients"]
        logs = [l for l in _logs() if "Hola" in l["subject"]]
        assert len(logs) == 3
        by_to = {l["to"][0]: l for l in logs}
        assert set(by_to) == {f"ana_{SUF}@example.com", f"ceci_{SUF}@example.com", f"eva_{SUF}@example.com"}
        ana = by_to[f"ana_{SUF}@example.com"]
        assert ana["subject"] == f"TEST343 {SUF} Hola TEST Ana de TEST_BANCO_A_{SUF}"
        assert ana["bcc_count"] == 0
        assert "TEST Ana (Gerente)" in ana["html_preview"] and "0412-1" in ana["html_preview"]
        assert "J-111 0991" in ana["html_preview"]
        eva = by_to[f"eva_{SUF}@example.com"]
        assert eva["subject"].endswith(f"TEST Eva de TEST_BANCO_B_{SUF}")
        assert "J-222 0992" in eva["html_preview"]
        assert all("{contacto_" not in l["subject"] + l["html_preview"] for l in logs)

    def test_per_bank(self, H):
        r = _send(H, SEL, T_BANK)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["send_mode"] == "per_bank" and b["batches_count"] == 2
        logs = [l for l in _logs() if "Aviso" in l["subject"]]
        assert len(logs) == 2
        subj = {l["subject"]: l for l in logs}
        a = subj[f"TEST343 {SUF} Aviso a TEST_BANCO_A_{SUF}"]
        assert a["bcc_count"] == 2  # Ana + Ceci (Beto deselected)
        assert "RIF J-111 tipo Banco pais Venezuela proc PROC_A" in a["html_preview"]
        bb = subj[f"TEST343 {SUF} Aviso a TEST_BANCO_B_{SUF}"]
        assert bb["bcc_count"] == 1 and "PROC_B" in bb["html_preview"]
        assert all(f"beto_{SUF}" not in json.dumps(l["to"]) for l in logs)

    def test_single_bcc(self, H):
        r = _send(H, SEL, T_NONE)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["send_mode"] == "single_bcc" and b["batches_count"] == 1
        logs = [l for l in _logs() if "General" in l["subject"]]
        assert len(logs) == 1 and logs[0]["bcc_count"] == 3

    def test_double_brace_bank_var(self, H):
        r = _send(H, SEL, T_DOUBLE)
        assert r.status_code == 200, r.text
        assert r.json()["send_mode"] == "per_bank"
        subs = sorted(l["subject"] for l in _logs() if " D " in l["subject"])
        assert subs == sorted([f"TEST343 {SUF} D TEST_BANCO_A_{SUF}", f"TEST343 {SUF} D TEST_BANCO_B_{SUF}"])

    def test_bitacora_send_mode(self, H):
        async def q(db):
            return [d async for d in db.bitacora.find({"action": "bank_mass_communication", "template_id": {"$in": ALL_TPL}}, {"_id": 0})]
        rows = {r["template_id"]: r for r in _run(_db_op(q))}
        assert rows[T_CONTACT]["send_mode"] == "per_contact" and rows[T_CONTACT]["batches_count"] == 3
        assert rows[T_BANK]["send_mode"] == "per_bank" and rows[T_BANK]["batches_count"] == 2
        assert rows[T_NONE]["send_mode"] == "single_bcc" and rows[T_NONE]["batches_count"] == 1
