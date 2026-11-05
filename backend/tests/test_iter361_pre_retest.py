# ruff: noqa
"""Iter361 — Retest Cotizaciones Preliminares (PRE).
Cubre: Modificar (/duplicate in_place/new_version) en PRE, búsqueda de clientes sin placeholder,
envío por correo de PRE sin PDF (regenera), bloqueos y asignación → COT.
Los quote_id creados se registran en /tmp/iter361_created.txt para limpieza posterior (notes TEST_ITER361)."""
import os
import re
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
SIN_RIF = "cli_sin_rif"
PRE_MSG = ("Acción no permitida: La cotización preliminar debe ser asignada a un cliente formal "
           "antes de continuar el flujo operativo.")
PRE_RE = re.compile(r"^PRE-\d{4}-\d{2}-\d{4}-(PYME|CORP)$")
COT_RE = re.compile(r"^COT-\d{4}-\d{2}-\d{3}-(PYME|CORP)$")
TRACK = "/tmp/iter361_created.txt"


def _track(qid):
    if qid:
        with open(TRACK, "a") as f:
            f.write(qid + "\n")


@pytest.fixture(scope="module")
def H():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}, timeout=30)
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    return {"Authorization": "Bearer " + r.json()["session_token"]}


@pytest.fixture(scope="module")
def real_client(H):
    cl = requests.get(f"{BASE_URL}/api/clients", headers=H, timeout=30).json()
    return next(c for c in cl if c.get("rif") and not c.get("is_placeholder"))


def _vpos(H, client_id):
    payload = {
        "client_id": client_id, "quote_category": "implementation", "quote_type": "VPOS",
        "services": [{"item_id": f"svc_{uuid.uuid4().hex[:8]}", "item_name": "TEST_ITER361_svc", "item_type": "setup",
                      "unit_price_usd": 100.0, "quantity": 1, "total_usd": 100.0, "cantidad_cajas": 1, "cantidad_bancos": 1}],
        "hardware": [], "equipment_items": [], "cantidad_cajas": 1, "cantidad_bancos": 1,
        "notes": "TEST_ITER361", "client_segment": "PYME",
    }
    r = requests.post(f"{BASE_URL}/api/quotes", headers=H, json=payload, timeout=60)
    assert r.status_code in (200, 201), r.text[:400]
    d = r.json()
    _track(d["quote_id"])
    return d


def _equip(H, eq_type="Reparación"):
    payload = {
        "client_id": SIN_RIF, "cliente_nombre": "Cliente Sin Rif", "cliente_rif": "J000000000",
        "cliente_address": "", "equipment_type": eq_type,
        "items": [{"hardware_id": "", "name": "TEST_ITER361 Servicio", "hardware_type": "Servicio",
                   "quantity": 1, "unit_price_usd": 50.0, "total_usd": 50.0, "serials": []}],
        "notes": "TEST_ITER361", "repair_description": "TEST_ITER361", "equipment_serial_number": "",
        "estimated_delivery_date": "", "bulk_serials": [], "repair_models": [],
    }
    r = requests.post(f"{BASE_URL}/api/quotes/generate-equipment-pdf", headers=H, json=payload, timeout=90)
    assert r.status_code == 200, r.text[:400]
    qid = r.headers.get("X-Quote-Id")
    _track(qid)
    return {"quote_id": qid, "quote_number": r.headers.get("X-Quote-Number")}


# --- clients/search: placeholder oculto salvo include_placeholder ---
class TestClientSearch:
    def test_search_hides_placeholder(self, H):
        for q in ("Sin Rif", "J000000000", ""):
            r = requests.get(f"{BASE_URL}/api/clients/search", params={"q": q}, headers=H, timeout=30)
            assert r.status_code == 200
            assert all(c["client_id"] != SIN_RIF for c in r.json()), q

    def test_search_include_placeholder(self, H):
        r = requests.get(f"{BASE_URL}/api/clients/search", params={"q": "Sin Rif", "include_placeholder": "true"},
                         headers=H, timeout=30)
        assert any(c["client_id"] == SIN_RIF for c in r.json())

    def test_clients_include_placeholder_first(self, H):
        cl = requests.get(f"{BASE_URL}/api/clients?include_placeholder=true", headers=H, timeout=30).json()
        assert cl[0]["client_id"] == SIN_RIF


# --- Modificar en PRE ---
class TestPreModify:
    def test_in_place_keeps_pre(self, H):
        pre = _vpos(H, SIN_RIF)
        assert PRE_RE.match(pre["quote_number"])
        r = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/duplicate", headers=H,
                          params={"mode": "in_place"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["new_quote_id"] == pre["quote_id"] and d["new_quote_number"] == pre["quote_number"]

    def test_new_version_stays_pre(self, H):
        pre = _equip(H)
        r = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/duplicate", headers=H,
                          params={"mode": "new_version"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        _track(d.get("new_quote_id"))
        assert PRE_RE.match(d["new_quote_number"]), d
        q = requests.get(f"{BASE_URL}/api/quotes/{d['new_quote_id']}", headers=H, timeout=30).json()
        assert q["client_id"] == SIN_RIF and q["quote_number"] == d["new_quote_number"]
        # La nueva versión sigue bloqueada
        r2 = requests.post(f"{BASE_URL}/api/quotes/{d['new_quote_id']}/approve", headers=H, json={}, timeout=30)
        assert r2.status_code == 400 and r2.json()["detail"] == PRE_MSG

    def test_duplicate_without_mode_blocked(self, H):
        pre = _vpos(H, SIN_RIF)
        r = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/duplicate", headers=H, timeout=30)
        assert r.status_code == 400 and r.json()["detail"] == PRE_MSG


# --- Envío por correo de PRE sin PDF (regenera) ---
class TestSendNoPdf:
    def test_send_equipment_pre_without_pdf(self, H):
        pre = _equip(H, "Equipos")
        # Simula PRE sin PDF: new_version deja quote_pdf_url=None
        r = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/duplicate", headers=H,
                          params={"mode": "new_version"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        nid = r.json()["new_quote_id"]
        _track(nid)
        q = requests.get(f"{BASE_URL}/api/quotes/{nid}", headers=H, timeout=30).json()
        assert not q.get("quote_pdf_url")
        s = requests.post(f"{BASE_URL}/api/quotes/{nid}/send-preliminary", headers=H,
                          json={"email": "rgonzalez@megasoft.com.ve"}, timeout=120)
        assert s.status_code == 200, s.text[:300]
        assert "rgonzalez@megasoft.com.ve" in s.json()["message"]
        q2 = requests.get(f"{BASE_URL}/api/quotes/{nid}", headers=H, timeout=30).json()
        assert q2.get("quote_pdf_url"), "PDF no regenerado"

    def test_send_vpos_pre_without_pdf(self, H):
        pre = _vpos(H, SIN_RIF)  # POST /quotes no genera PDF
        s = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/send-preliminary", headers=H,
                          json={"email": "rgonzalez@megasoft.com.ve"}, timeout=120)
        assert s.status_code == 200, s.text[:300]


# --- Regresión: assign ---
class TestAssign:
    def test_assign_flow(self, H, real_client):
        pre = _vpos(H, SIN_RIF)
        r = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/assign-client", headers=H,
                          json={"client_id": real_client["client_id"]}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert COT_RE.match(d["quote_number"]) and d["preliminary_number"] == pre["quote_number"]
        r2 = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/assign-client", headers=H,
                           json={"client_id": real_client["client_id"]}, timeout=30)
        assert r2.status_code == 400
