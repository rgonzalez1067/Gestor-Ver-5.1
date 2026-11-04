"""iter346/347 — 'Enviar copia a' (copy_emails, BCC) en comunicaciones masivas a Integradores y Bancos/Entes.
Solo fixtures TEST_ con correos @example.com. Verifica parseo/dedupe, validaciones 400, copia en ENVÍO SEPARADO
(una vez, variables en blanco), bitácora y no-regresión sin copias. Correr con -p no:xdist."""
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
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"}
START = datetime.now(timezone.utc).isoformat()
SUF = uuid.uuid4().hex[:6]
B1, B2 = f"bnk_TEST_{SUF}a", f"bnk_TEST_{SUF}b"
I1, I2 = f"int_TEST_{SUF}1", f"int_TEST_{SUF}2"
T_CONTACT, T_BANK, T_NONE = (f"tpl_TEST_{SUF}_{x}" for x in ("c", "b", "n"))
ALL_TPL = [T_CONTACT, T_BANK, T_NONE]
CP1, CP2 = f"copia1_{SUF}@example.com", f"copia2_{SUF}@example.com"


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
        {"bank_id": B1, "name": f"TEST_BANCO_A_{SUF}", "rif": "J-111", "bank_code": "0991", "type": "Banco", "contacts": [
            {"full_name": "TEST Ana", "email": f"ana_{SUF}@example.com", "position": "Gerente", "phone": "1"},
            {"full_name": "TEST Ceci", "email": f"ceci_{SUF}@example.com", "position": "Jefe", "phone": "3"},
        ]},
        {"bank_id": B2, "name": f"TEST_BANCO_B_{SUF}", "rif": "J-222", "bank_code": "0992", "type": "Ente", "contacts": [
            {"full_name": "TEST Eva", "email": f"eva_{SUF}@example.com", "position": "Dir", "phone": "9"},
        ]},
    ]
    tpls = [
        {"template_id": T_CONTACT, "subject": f"TEST346 {SUF} Hola {{contacto_nombre}}", "body_html": "<p>{contacto_nombre}</p>"},
        {"template_id": T_BANK, "subject": f"TEST346 {SUF} Aviso {{banco_nombre}}", "body_html": "<p>{banco_nombre}</p>"},
        {"template_id": T_NONE, "subject": f"TEST346 {SUF} General", "body_html": "<p>Sin variables</p>"},
    ]
    ints = [
        {"integrator_id": I1, "name": f"TEST_INT1_{SUF}", "email": f"int1_{SUF}@example.com", "integration_type": "API"},
        {"integrator_id": I2, "name": f"TEST_INT2_{SUF}", "email": f"int2_{SUF}@example.com", "integration_type": "API"},
    ]

    async def setup(db):
        await db.banks.insert_many([dict(b) for b in banks])
        await db.integrators.insert_many([dict(i) for i in ints])
        await db.email_templates.insert_many([{**t, "context": "INTEGRADORES", "name": f"TEST_{t['template_id']}"} for t in tpls])
    _run(_db_op(setup))
    yield

    async def teardown(db):
        await db.banks.delete_many({"bank_id": {"$in": [B1, B2]}})
        await db.integrators.delete_many({"integrator_id": {"$in": [I1, I2]}})
        await db.email_templates.delete_many({"template_id": {"$in": ALL_TPL}})
        await db.bitacora.delete_many({"action": {"$in": ["bank_mass_communication", "integrator_mass_communication"]},
                                       "template_id": {"$in": ALL_TPL}})
        await db.email_logs.delete_many({"created_at": {"$gte": START}, "subject": {"$regex": f"^TEST346 {SUF}"}})
    _run(_db_op(teardown))


def _bank(H, tid, copy=None, keys=None):
    data = {"template_id": tid, "contact_keys": json.dumps(keys or SEL)}
    if copy is not None:
        data["copy_emails"] = copy
    return requests.post(f"{BASE_URL}/banks/mass/communication", headers=H, data=data, timeout=90)


def _int(H, tid, copy=None):
    data = {"template_id": tid, "integrator_ids": json.dumps([I1, I2])}
    if copy is not None:
        data["copy_emails"] = copy
    return requests.post(f"{BASE_URL}/integrators/mass/communication", headers=H, data=data, timeout=90)


def _logs(word, since):
    async def q(db):
        return [d async for d in db.email_logs.find(
            {"subject": {"$regex": f"^TEST346 {SUF}.*{word}"}, "created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", 1)]
    return _run(_db_op(q))


def _bita(action, tid):
    async def q(db):
        return [d async for d in db.bitacora.find({"action": action, "template_id": tid}, {"_id": 0}).sort("created_at", -1)]
    return _run(_db_op(q))


def _now():
    return datetime.now(timezone.utc).isoformat()


SEL = [f"{B1}::idx0", f"{B1}::idx1", f"{B2}::idx0"]


# Validación / parseo de copy_emails
class TestValidation:
    def test_int_invalid_copy_400(self, H):
        r = _int(H, T_NONE, "bad-email")
        assert r.status_code == 400 and "Correo en copia inválido" in r.json()["detail"]

    def test_bank_invalid_copy_400(self, H):
        r = _bank(H, T_NONE, f"{CP1}, nope@x")
        assert r.status_code == 400 and "Correo en copia inválido" in r.json()["detail"]

    def test_more_than_10_400(self, H):
        many = ",".join(f"c{i}_{SUF}@example.com" for i in range(11))
        r = _int(H, T_NONE, many)
        assert r.status_code == 400 and "Máximo 10" in r.json()["detail"]
        r2 = _bank(H, T_NONE, many)
        assert r2.status_code == 400 and "Máximo 10" in r2.json()["detail"]

    def test_invalid_does_not_send(self, H):
        assert _logs("General", START) == []  # las validaciones 400 no envían nada


# Integradores — single BCC; copia en envío separado (iter347)
class TestIntegrators:
    def test_int_copy_dedupe_separate_send(self, H):
        t0 = _now()
        r = _int(H, T_NONE, f"{CP1}; {CP2} {CP1.upper()},")
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["copy_emails"] == [CP1, CP2]
        logs = _logs("General", t0)
        assert len(logs) == 2, [(l["to"], l["bcc_count"]) for l in logs]
        assert logs[0]["bcc_count"] == 2  # lote principal: solo integradores
        assert logs[1]["bcc_count"] == 2  # copia aparte: 2 copias
        row = _bita("integrator_mass_communication", T_NONE)[0]
        assert row["copy_emails"] == [CP1, CP2] and row["batches_count"] == 1

    def test_int_no_copy_regression(self, H):
        t0 = _now()
        r = _int(H, T_NONE)
        assert r.status_code == 200, r.text
        assert r.json()["copy_emails"] == []
        logs = _logs("General", t0)
        assert len(logs) == 1 and logs[0]["bcc_count"] == 2
        assert _bita("integrator_mass_communication", T_NONE)[0]["copy_emails"] == []


# Bancos — single / per_contact / per_bank: copia una sola vez, aparte y en blanco
class TestBanks:
    def test_single_bcc_with_copy(self, H):
        t0 = _now()
        r = _bank(H, T_NONE, CP1)
        assert r.status_code == 200, r.text
        assert r.json()["send_mode"] == "single_bcc" and r.json()["copy_emails"] == [CP1]
        logs = _logs("General", t0)
        assert [l["bcc_count"] for l in logs] == [3, 1]

    def test_per_contact_copy_once_blank(self, H):
        t0 = _now()
        r = _bank(H, T_CONTACT, f"{CP1},{CP2}")
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["send_mode"] == "per_contact" and b["batches_count"] == 3
        assert b["copy_emails"] == [CP1, CP2]
        logs = _logs("Hola", t0)
        assert len(logs) == 4, [(l["to"], l["bcc_count"]) for l in logs]
        assert [l["bcc_count"] for l in logs] == [0, 0, 0, 2]
        copy = logs[-1]
        assert "{" not in copy["subject"] and "TEST" not in copy["subject"].split("Hola", 1)[1]
        assert "{contacto" not in copy["html_preview"] and "TEST Ana" not in copy["html_preview"]
        assert any("TEST Ana" in l["subject"] for l in logs[:3])
        row = _bita("bank_mass_communication", T_CONTACT)[0]
        assert row["copy_emails"] == [CP1, CP2] and row["send_mode"] == "per_contact"

    def test_per_bank_copy_once_blank(self, H):
        t0 = _now()
        r = _bank(H, T_BANK, CP1)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["send_mode"] == "per_bank" and b["batches_count"] == 2
        logs = _logs("Aviso", t0)
        assert len(logs) == 3
        mains, copy = logs[:2], logs[2]
        assert sorted(l["bcc_count"] for l in mains) == [1, 2]  # sin copias en lotes
        assert copy["bcc_count"] == 1
        assert "BANCO" not in copy["subject"] and "{" not in copy["subject"]
        assert "BANCO" not in copy["html_preview"] and "{banco" not in copy["html_preview"]

    def test_copy_equal_to_recipient_excluded(self, H):
        t0 = _now()
        r = _bank(H, T_NONE, f"ANA_{SUF}@example.com")  # coincide con contacto (case-insensitive)
        assert r.status_code == 200, r.text
        logs = _logs("General", t0)
        assert [l["bcc_count"] for l in logs] == [3]  # no hay envío de copia

    def test_per_contact_no_copy_regression(self, H):
        t0 = _now()
        r = _bank(H, T_CONTACT)
        assert r.status_code == 200, r.text
        assert r.json()["copy_emails"] == []
        logs = _logs("Hola", t0)
        assert len(logs) == 3 and all(l["bcc_count"] == 0 for l in logs)

    def test_empty_copy_string_ok(self, H):
        r = _bank(H, T_NONE, "   ")
        assert r.status_code == 200 and r.json()["copy_emails"] == []


# Unit: _mass_dispatch con send_email mockeado (listas BCC exactas, CSS intacto)
import sys
sys.path.insert(0, "/app/backend")


class _FakeColl:
    def __init__(self):
        self.docs = []

    async def insert_one(self, d):
        self.docs.append(d)

    async def find_one(self, *a, **k):
        return None


class _FakeDB:
    def __init__(self):
        self.bitacora = _FakeColl()
        self.email_templates = _FakeColl()
        self.entity_documents = _FakeColl()


@pytest.fixture
def dispatch(monkeypatch):
    import routes.entity_communications as m
    calls = []

    async def fake_send(**kw):
        calls.append(kw)
        return {"status": "sent"}

    async def fake_sender(area):
        return "sender@example.com"

    async def fake_sig(u):
        return "<b>FIRMA_OK</b>"

    monkeypatch.setattr(m, "send_email", fake_send)
    monkeypatch.setattr(m, "resolve_sender_for_area", fake_sender)
    monkeypatch.setattr(m, "build_signature_html", fake_sig)
    monkeypatch.setattr(m, "db", _FakeDB())

    def run(recipients, tpl, batches=None, copies=None):
        calls.clear()
        _run(m._mass_dispatch(recipients, tpl["template_id"], "[]", [], {"email": "u@example.com"},
                              folder="tmp_test_iter347", action="x", target_label="t",
                              batches=batches, tpl=tpl, copy_emails=copies))
        return calls
    return run, m


TPL_U = {"template_id": "tpl_unit", "subject": "Hola {contacto_nombre} {{banco_nombre}} {fecha_sistema}",
         "body_html": "<style>p {margin:0} .a{color:red}</style><p>{contacto_nombre} de {banco_nombre}</p>{Firma_Notificacion_Global}"}


class TestDispatchUnit:
    def test_per_contact_copy_once_blank(self, dispatch):
        run, _ = dispatch
        bt = [{"to": [f"r{i}@example.com"], "bcc": False, "vars": {"contacto_nombre": f"NOMBRE{i}", "banco_nombre": "BANCOX"}}
              for i in range(3)]
        calls = run([f"r{i}@example.com" for i in range(3)], TPL_U, bt, ["c1@example.com", "R1@example.com", "c2@example.com"])
        assert len(calls) == 4
        for c in calls[:3]:
            assert not c.get("bcc")  # sin copias en lotes
        cp = calls[3]
        assert cp["to"] == ["sender@example.com"] and cp["bcc"] == ["c1@example.com", "c2@example.com"]
        assert "{" not in cp["subject"] and "NOMBRE" not in cp["subject"] and "BANCOX" not in cp["subject"]
        assert "NOMBRE" not in cp["html"] and "BANCOX" not in cp["html"] and "{contacto" not in cp["html"]
        assert "FIRMA_OK" in cp["html"] and "/" in cp["subject"]  # sistema renderizado (fecha)
        assert "p {margin:0}" in cp["html"] and ".a{color:red}" in cp["html"]
        assert "NOMBRE0" in calls[0]["subject"] and "p {margin:0}" in calls[0]["html"]

    def test_single_bcc_copy_separate(self, dispatch):
        run, _ = dispatch
        rec = ["a@example.com", "b@example.com"]
        calls = run(rec, TPL_U, None, ["c1@example.com"])
        assert len(calls) == 2
        assert calls[0]["bcc"] == rec
        assert calls[1]["bcc"] == ["c1@example.com"] and "{" not in calls[1]["subject"]

    def test_per_bank_copy_once(self, dispatch):
        run, _ = dispatch
        bt = [{"to": ["a@example.com", "b@example.com"], "bcc": True, "vars": {"banco_nombre": "BA"}},
              {"to": ["c@example.com"], "bcc": True, "vars": {"banco_nombre": "BB"}}]
        calls = run(["a@example.com", "b@example.com", "c@example.com"], TPL_U, bt, ["k@example.com"])
        assert len(calls) == 3
        assert calls[0]["bcc"] == ["a@example.com", "b@example.com"] and calls[1]["bcc"] == ["c@example.com"]
        assert calls[2]["bcc"] == ["k@example.com"] and "BA" not in calls[2]["html"].replace("BANCO", "")

    def test_no_copy_no_extra_send(self, dispatch):
        run, _ = dispatch
        assert len(run(["a@example.com"], TPL_U, None, [])) == 1
        assert len(run(["a@example.com"], TPL_U, None, None)) == 1

    def test_copy_all_recipients_no_extra(self, dispatch):
        run, _ = dispatch
        assert len(run(["a@example.com"], TPL_U, None, ["A@example.com"])) == 1

    def test_copy_failure_reported(self, dispatch, monkeypatch):
        run, m = dispatch
        seen = []

        async def flaky(**kw):
            seen.append(kw)
            if len(seen) == 2:
                raise RuntimeError("smtp down")
            return {"status": "sent"}
        monkeypatch.setattr(m, "send_email", flaky)
        _run(m._mass_dispatch(["a@example.com"], "t", "[]", [], {"email": "u@example.com"}, folder="tmp_test_iter347",
                              action="x", target_label="t", tpl=TPL_U, copy_emails=["k@example.com"]))
        assert len(seen) == 2
