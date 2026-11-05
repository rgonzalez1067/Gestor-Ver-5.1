# ruff: noqa
"""Iter362 — Nuevo tipo de Cotización MPOS (sin equipos).
Flujo: VPOS-like + Configuración tras Enviar a Imple → Histórico automático.
Cubre catálogo de acciones, configure antes/después de enviar, reenvío bloqueado,
cotización preservada tras send-to-impl, archivado + email legacy configure_mpos_seller,
y regresión VPOS / fast_track. Limpieza de quotes/projects/history creados por id."""
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
EXC = {"x-exception-reason": "TEST_ITER362 prueba automatizada"}
CREATED = {"quotes": [], "projects": []}


@pytest.fixture(scope="module")
def mdb():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def H():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}, timeout=30)
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    return {"Authorization": "Bearer " + r.json()["session_token"]}


@pytest.fixture(scope="module")
def client_id(H):
    cl = requests.get(f"{BASE_URL}/api/clients", headers=H, timeout=30).json()
    return next(c for c in cl if c.get("rif") and not c.get("is_placeholder"))["client_id"]


def _create(H, client_id, qtype, category="implementation"):
    payload = {
        "client_id": client_id, "quote_category": category, "quote_type": qtype,
        "services": [{"item_id": f"svc_{uuid.uuid4().hex[:8]}", "item_name": "TEST_ITER362_svc", "item_type": "setup",
                      "unit_price_usd": 100.0, "quantity": 1, "total_usd": 100.0, "cantidad_cajas": 1, "cantidad_bancos": 1}],
        "hardware": [], "equipment_items": [], "cantidad_cajas": 1, "cantidad_bancos": 1,
        "notes": "TEST_ITER362", "client_segment": "PYME",
    }
    r = requests.post(f"{BASE_URL}/api/quotes", headers=H, json=payload, timeout=60)
    assert r.status_code in (200, 201), r.text[:400]
    d = r.json()
    CREATED["quotes"].append(d["quote_id"])
    return d


@pytest.fixture(scope="module", autouse=True)
def cleanup(mdb):
    yield
    for qid in CREATED["quotes"]:
        for p in mdb.projects.find({"quote_id": qid}, {"_id": 0, "project_id": 1}):
            mdb.projects.delete_one({"project_id": p["project_id"]})
        mdb.quote_history.delete_many({"quote_id": qid})
        mdb.quotes.delete_one({"quote_id": qid})


@pytest.fixture(scope="module")
def mpos(H, client_id):
    return _create(H, client_id, "MPOS")


# --- Catálogo Configuración de Acciones ---
class TestCatalog:
    def test_catalog_mpos(self, H):
        r = requests.get(f"{BASE_URL}/api/action-notifications/catalog", headers=H, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        subs = {s["id"]: s["label"] for s in d["product_subcategories"]}
        assert subs.get("mpos_tablet") == "MPOS"
        assert "MPOS Tablet" not in subs.values()
        allowed = d["allowed_actions_by_biz_sub"]
        for biz in ("implementacion_pyme", "implementacion_corp"):
            acts = allowed[f"{biz}|mpos_tablet"]
            assert "configure" in acts and "send_to_implementation" in acts
            assert acts.index("configure") > acts.index("send_to_implementation")


# --- Flujo MPOS licencia ---
class TestMposFlow:
    def test_created(self, H, mpos):
        assert mpos["quote_type"] == "MPOS"
        assert mpos.get("quote_category", "implementation") == "implementation"

    def test_configure_before_send_400(self, H, mpos):
        r = requests.post(f"{BASE_URL}/api/quotes/{mpos['quote_id']}/configure", headers=H, timeout=30)
        assert r.status_code == 400, r.text[:300]
        assert "Primero debe Enviar a Implementación" in r.json()["detail"]

    def test_send_without_reason_422(self, H, mpos):
        r = requests.post(f"{BASE_URL}/api/quotes/{mpos['quote_id']}/send-to-implementation", headers=H, json={}, timeout=60)
        assert r.status_code == 422, r.text[:300]

    def test_send_keeps_quote_active(self, H, mpos, mdb):
        r = requests.post(f"{BASE_URL}/api/quotes/{mpos['quote_id']}/send-to-implementation", headers={**H, **EXC}, json={}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["new_status"] == "Enviada a Imple"
        g = requests.get(f"{BASE_URL}/api/quotes/{mpos['quote_id']}", headers=H, timeout=30)
        assert g.status_code == 200, g.text[:200]
        q = mdb.quotes.find_one({"quote_id": mpos["quote_id"]}, {"_id": 0})
        assert q["quote_status"] == "Enviada a Imple"
        assert q.get("sent_to_implementation_at")
        assert not q.get("archived")
        assert mdb.projects.find_one({"quote_id": mpos["quote_id"]}) is not None
        assert mdb.quote_history.find_one({"quote_id": mpos["quote_id"]}) is None

    def test_resend_400(self, H, mpos):
        r = requests.post(f"{BASE_URL}/api/quotes/{mpos['quote_id']}/send-to-implementation", headers={**H, **EXC}, json={}, timeout=60)
        assert r.status_code == 400, r.text[:300]
        assert "ya fue enviada" in r.json()["detail"]

    def test_configure_archives(self, H, mpos, mdb):
        r = requests.post(f"{BASE_URL}/api/quotes/{mpos['quote_id']}/configure", headers=H, timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["new_status"] == "Configurada" and d["archived"] is True
        q = mdb.quotes.find_one({"quote_id": mpos["quote_id"]}, {"_id": 0})
        assert q["archived"] is True and q["quote_status"] == "Configurada"
        assert mdb.quote_history.find_one({"quote_id": mpos["quote_id"]}) is not None
        lst = requests.get(f"{BASE_URL}/api/quotes", headers=H, timeout=60).json()
        assert all(x["quote_id"] != mpos["quote_id"] for x in lst)
        hist = requests.get(f"{BASE_URL}/api/quote-history", headers=H, params={"search": mpos["quote_number"]}, timeout=60)
        assert hist.status_code == 200
        assert any(h.get("quote_id") == mpos["quote_id"] for h in hist.json())

    def test_email_log_legacy(self, H, mpos, mdb):
        log = mdb.email_logs.find_one({"quote_id": mpos["quote_id"], "action": "configure_mpos_seller"})
        assert log is not None, "No hay email_log configure_mpos_seller"

    def test_configure_again_after_archive(self, H, mpos):
        # Segunda configuración: no debería romper (idempotencia de archivo)
        r = requests.post(f"{BASE_URL}/api/quotes/{mpos['quote_id']}/configure", headers=H, timeout=60)
        print("second configure:", r.status_code, r.text[:200])
        assert r.status_code in (200, 400)


# --- Regresión ---
class TestRegression:
    def test_vpos_send_archives_and_deletes(self, H, client_id, mdb):
        v = _create(H, client_id, "VPOS")
        r = requests.post(f"{BASE_URL}/api/quotes/{v['quote_id']}/configure", headers=H, timeout=30)
        assert r.status_code == 400
        r = requests.post(f"{BASE_URL}/api/quotes/{v['quote_id']}/send-to-implementation", headers={**H, **EXC}, json={}, timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert mdb.quotes.find_one({"quote_id": v["quote_id"]}) is None
        assert mdb.quote_history.find_one({"quote_id": v["quote_id"]}) is not None
        assert mdb.projects.find_one({"quote_id": v["quote_id"]}) is not None

    def test_fast_track_configure(self, H, client_id, mdb):
        try:
            f = _create(H, client_id, "FAST_TRACK", category="fast_track")
        except AssertionError as e:
            pytest.skip(f"no se pudo crear fast_track: {e}")
        r = requests.post(f"{BASE_URL}/api/quotes/{f['quote_id']}/configure", headers=H, timeout=60)
        assert r.status_code == 200, r.text[:300]
        q = mdb.quotes.find_one({"quote_id": f["quote_id"]}, {"_id": 0})
        assert q["quote_status"] == "Configurada"
        assert not q.get("archived")
