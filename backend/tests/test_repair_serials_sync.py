# Repair quote serial management: sync on PUT, transfer on new_version, in_place, non-repair, reception PDF logo
import os
import io
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "admin123"}

_mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
mdb = _mc[os.environ.get("DB_NAME", "test_database")]

SUF = uuid.uuid4().hex[:5].upper()
S1, S2, S3 = f"TST-S1-{SUF}", f"TST-S2-{SUF}", f"TST-S3-{SUF}"
STATE = {"quotes": []}


@pytest.fixture(scope="module")
def h():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("session_token") or r.json().get("token")
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    mdb.taller_equipos.delete_many({"serial": {"$regex": f"^TST-.*{SUF}$"}})
    if STATE.get("client_id"):
        mdb.clients.delete_many({"client_id": STATE["client_id"]})
    if STATE["quotes"]:
        mdb.quotes.delete_many({"quote_id": {"$in": STATE["quotes"]}})
        mdb.bitacora.delete_many({"$or": [{"quote_id": {"$in": STATE["quotes"]}},
                                          {"new_quote_id": {"$in": STATE["quotes"]}}]})


def te(serial):
    return mdb.taller_equipos.find_one({"serial": serial}, {"_id": 0})


def q(qid):
    return mdb.quotes.find_one({"quote_id": qid}, {"_id": 0})


def item(name, qty, serials):
    return {"name": name, "hardware_id": "", "hardware_type": "Servicio", "quantity": qty,
            "unit_price_usd": 10, "total_usd": 10 * qty, "serials": serials}


def put_items(h, qid, items):
    return requests.put(f"{BASE_URL}/api/quotes/{qid}", headers=h, json={"equipment_items": items}, timeout=60)


class TestRepairSerials:
    def test_01_client_and_reception(self, h):
        rif = f"J-{uuid.uuid4().int % 100000000:08d}-1"
        r = requests.post(f"{BASE_URL}/api/clients", headers=h, json={
            "rif": rif, "legal_name": f"TEST_Cliente {SUF}", "fantasy_name": f"TEST_Cliente {SUF}"}, timeout=30)
        assert r.status_code in (200, 201), r.text
        cid = r.json().get("client_id") or (r.json().get("client") or {}).get("client_id")
        assert cid, r.json()
        STATE["client_id"] = cid
        r = requests.post(f"{BASE_URL}/api/taller/recepcion", headers=h, json={
            "client_id": cid, "models": [{"model_name": "TEST Modelo", "serials": [S1, S2, S3]}]}, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["created"] == 3
        for s in (S1, S2, S3):
            d = te(s)
            assert d["estatus"] == "Recibido" and d["quote_id"] is None

    def test_02_reception_pdf_with_logo(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.quote_taller import _generate_reception_pdf
        from config import UPLOADS_DIR
        assert (UPLOADS_DIR / "logo.png").exists() or list(UPLOADS_DIR.glob("logo.*"))
        pdf = _generate_reception_pdf("TEST Cliente", "J-1", [("TEST Modelo", S1)], "01/01/2026 10:00", "a@b.c")
        assert pdf[:4] == b"%PDF"
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        page = PdfReader(io.BytesIO(pdf)).pages[0]
        xobj = page["/Resources"].get("/XObject")
        assert xobj is not None and len(xobj) >= 1, "Logo image not embedded in reception PDF"

    def test_03_create_repair_quote(self, h):
        cid = STATE["client_id"]
        ids = [te(S1)["taller_equipo_id"], te(S2)["taller_equipo_id"]]
        r = requests.post(f"{BASE_URL}/api/quotes/generate-equipment-pdf", headers=h, json={
            "client_id": cid, "cliente_nombre": f"TEST_Cliente {SUF}", "equipment_type": "Reparación",
            "items": [item("TEST Servicio A", 2, [S1, S2]), item("TEST Servicio B", 1, [S1])],
            "repair_models": [{"model_name": "TEST Modelo", "quantity": 2, "serials": [S1, S2]}],
            "linked_taller_equipo_ids": ids}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        qid = r.headers.get("X-Quote-Id")
        assert qid
        STATE["quotes"].append(qid)
        STATE["q1"], STATE["q1num"] = qid, r.headers.get("X-Quote-Number")
        for s in (S1, S2):
            d = te(s)
            assert d["estatus"] == "Cotizado" and d["quote_id"] == qid
        assert te(S3)["estatus"] == "Recibido"
        assert q(qid)["quote_category"] == "repair"

    def test_04_put_release_s2_keep_s1_multiline(self, h):
        qid = STATE["q1"]
        r = put_items(h, qid, [item("TEST Servicio A", 1, [S1]), item("TEST Servicio B", 1, [S1])])
        assert r.status_code == 200, r.text
        d2 = te(S2)
        assert d2["estatus"] == "Recibido" and d2["quote_id"] is None and d2["quote_number"] is None
        d1 = te(S1)
        assert d1["estatus"] == "Cotizado" and d1["quote_id"] == qid
        doc = q(qid)
        assert doc["linked_taller_equipo_ids"] == [d1["taller_equipo_id"]]
        pool = [s for m in doc["repair_models"] for s in m["serials"]]
        assert pool == [S1]

    def test_05_put_add_s3(self, h):
        qid = STATE["q1"]
        r = put_items(h, qid, [item("TEST Servicio A", 1, [S1]), item("TEST Servicio B", 1, [S1]),
                               item("TEST Servicio C", 1, [S3])])
        assert r.status_code == 200, r.text
        d3 = te(S3)
        assert d3["estatus"] == "Cotizado" and d3["quote_id"] == qid
        doc = q(qid)
        assert set(doc["linked_taller_equipo_ids"]) == {te(S1)["taller_equipo_id"], d3["taller_equipo_id"]}
        pool = {s for m in doc["repair_models"] for s in m["serials"]}
        assert pool == {S1, S3}

    def test_06_duplicate_new_version_transfers(self, h):
        qid = STATE["q1"]
        r = requests.post(f"{BASE_URL}/api/quotes/{qid}/duplicate?mode=new_version", headers=h, timeout=60)
        assert r.status_code == 200, r.text
        nid, nnum = r.json()["new_quote_id"], r.json()["new_quote_number"]
        STATE["quotes"].append(nid)
        STATE["q2"] = nid
        assert nid != qid
        for s in (S1, S3):
            d = te(s)
            assert d["estatus"] == "Cotizado" and d["quote_id"] == nid and d["quote_number"] == nnum
        orig = q(qid)
        assert orig["linked_taller_equipo_ids"] == []
        assert set(orig["released_taller_equipo_ids"]) == {te(S1)["taller_equipo_id"], te(S3)["taller_equipo_id"]}
        new = q(nid)
        assert new["quote_status"] == "Borrador"
        pool = {s for m in new["repair_models"] for s in m["serials"]}
        assert pool == {S1, S3}

    def test_07_new_version_put_unmark_s3(self, h):
        nid = STATE["q2"]
        r = put_items(h, nid, [item("TEST Servicio A", 1, [S1]), item("TEST Servicio B", 1, [S1])])
        assert r.status_code == 200, r.text
        d3 = te(S3)
        assert d3["estatus"] == "Recibido" and d3["quote_id"] is None
        assert te(S1)["quote_id"] == nid
        # original must remain unaffected
        assert q(STATE["q1"])["linked_taller_equipo_ids"] == []

    def test_08_in_place_then_put_sync(self, h):
        nid = STATE["q2"]
        r = requests.post(f"{BASE_URL}/api/quotes/{nid}/duplicate?mode=in_place", headers=h, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["new_quote_id"] == nid
        r = put_items(h, nid, [item("TEST Servicio A", 2, [S1, S2])])
        assert r.status_code == 200, r.text
        assert te(S2)["estatus"] == "Cotizado" and te(S2)["quote_id"] == nid
        r = put_items(h, nid, [item("TEST Servicio A", 1, [S2])])
        assert r.status_code == 200, r.text
        assert te(S1)["estatus"] == "Recibido" and te(S1)["quote_id"] is None
        assert te(S2)["quote_id"] == nid
        assert q(nid)["linked_taller_equipo_ids"] == [te(S2)["taller_equipo_id"]]

    def test_09_non_repair_put_does_not_touch_taller(self, h):
        cid = STATE["client_id"]
        r = requests.post(f"{BASE_URL}/api/quotes/generate-equipment-pdf", headers=h, json={
            "client_id": cid, "cliente_nombre": f"TEST_Cliente {SUF}", "equipment_type": "Accesorio",
            "items": [item("TEST Accesorio", 1, [])]}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        eq = r.headers.get("X-Quote-Id")
        STATE["quotes"].append(eq)
        before = {s: te(s) for s in (S1, S2, S3)}
        r = put_items(h, eq, [item("TEST Accesorio", 1, [S1, S3])])
        assert r.status_code == 200, r.text
        after = {s: te(s) for s in (S1, S2, S3)}
        for s in (S1, S2, S3):
            assert before[s]["estatus"] == after[s]["estatus"] and before[s]["quote_id"] == after[s]["quote_id"]
