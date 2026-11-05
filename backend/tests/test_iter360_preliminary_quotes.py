# ruff: noqa
"""Iter360 — Cotizaciones Preliminares (Cliente Sin Rif, prefijo PRE).
Cubre: ocultamiento del placeholder, numeración PRE, bloqueo de acciones,
Modificar (duplicate) en PRE, envío por correo, asignación a cliente → COT, regresión COT.
Los quote_id creados se registran en /tmp/iter360_created.txt para limpieza posterior."""
import os
import re
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
SIN_RIF = "cli_sin_rif"
PRE_MSG = ("Acción no permitida: La cotización preliminar debe ser asignada a un cliente formal "
           "antes de continuar el flujo operativo.")
PRE_RE = re.compile(r"^PRE-\d{4}-\d{2}-\d{4}-(PYME|CORP)$")
COT_RE = re.compile(r"^COT-\d{4}-\d{2}-\d{3}-(PYME|CORP)$")
TRACK = "/tmp/iter360_created.txt"


def _track(qid):
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


def _vpos(H, client_id, segment="PYME"):
    payload = {
        "client_id": client_id, "quote_category": "implementation", "quote_type": "VPOS",
        "services": [{"item_id": f"svc_{uuid.uuid4().hex[:8]}", "item_name": "TEST_ITER360_svc", "item_type": "setup",
                      "unit_price_usd": 100.0, "quantity": 1, "total_usd": 100.0, "cantidad_cajas": 1, "cantidad_bancos": 1}],
        "hardware": [], "equipment_items": [], "cantidad_cajas": 1, "cantidad_bancos": 1,
        "notes": "TEST_ITER360", "client_segment": segment,
    }
    r = requests.post(f"{BASE_URL}/api/quotes", headers=H, json=payload, timeout=60)
    assert r.status_code in (200, 201), r.text[:400]
    d = r.json()
    _track(d["quote_id"])
    return d


@pytest.fixture(scope="module")
def pre_repair(H):
    payload = {
        "client_id": SIN_RIF, "cliente_nombre": "Cliente Sin Rif", "cliente_rif": "J000000000",
        "cliente_address": "", "equipment_type": "Reparación",
        "items": [{"hardware_id": "", "name": "TEST_ITER360 Servicio Reparación", "hardware_type": "Servicio",
                   "quantity": 1, "unit_price_usd": 50.0, "total_usd": 50.0, "serials": []}],
        "notes": "TEST_ITER360", "repair_description": "TEST_ITER360", "equipment_serial_number": "",
        "estimated_delivery_date": "", "bulk_serials": [], "repair_models": [],
    }
    r = requests.post(f"{BASE_URL}/api/quotes/generate-equipment-pdf", headers=H, json=payload, timeout=90)
    assert r.status_code == 200, r.text[:400]
    qid = r.headers.get("X-Quote-Id")
    _track(qid)
    return {"quote_id": qid, "quote_number": r.headers.get("X-Quote-Number")}


# --- Directorio de clientes ---
class TestClientsPlaceholder:
    def test_hidden_by_default(self, H):
        cl = requests.get(f"{BASE_URL}/api/clients", headers=H, timeout=30).json()
        assert all(c["client_id"] != SIN_RIF for c in cl)

    def test_include_placeholder_first(self, H):
        cl = requests.get(f"{BASE_URL}/api/clients?include_placeholder=true", headers=H, timeout=30).json()
        assert cl[0]["client_id"] == SIN_RIF and cl[0]["rif"] == "J000000000"


# --- Numeración y bloqueo ---
class TestPreNumbering:
    def test_vpos_pre_number(self, H):
        d = _vpos(H, SIN_RIF)
        assert PRE_RE.match(d["quote_number"]), d["quote_number"]

    def test_repair_pre_number(self, pre_repair):
        assert PRE_RE.match(pre_repair["quote_number"]), pre_repair["quote_number"]

    def test_regression_real_client_cot(self, H, real_client):
        d = _vpos(H, real_client["client_id"])
        assert COT_RE.match(d["quote_number"]), d["quote_number"]


class TestPreBlocked:
    @pytest.mark.parametrize("method,action,body", [
        ("post", "approve", {}), ("get", "pdf", None), ("put", "status", {"quote_status": "Enviada"}),
        ("post", "send-to-client", {}), ("post", "invoice", {}), ("post", "collect", {}),
        ("post", "deliver", {}), ("post", "repair-complete", {}), ("post", "send-to-implementation", {}),
        ("post", "configure", {}), ("post", "repair-deliver", {}),
    ])
    def test_blocked(self, H, pre_repair, method, action, body):
        r = getattr(requests, method)(f"{BASE_URL}/api/quotes/{pre_repair['quote_id']}/{action}", headers=H,
                                      json=body, timeout=30)
        assert r.status_code == 400, f"{action}: {r.status_code} {r.text[:200]}"
        assert r.json()["detail"] == PRE_MSG


# --- Modificar Cotización (usa /duplicate con mode) debe funcionar en PRE ---
class TestPreModify:
    @pytest.mark.parametrize("mode", ["in_place", "new_version"])
    def test_modify_duplicate_allowed(self, H, pre_repair, mode):
        r = requests.post(f"{BASE_URL}/api/quotes/{pre_repair['quote_id']}/duplicate", headers=H,
                          params={"mode": mode}, timeout=60)
        if r.status_code == 200 and r.json().get("new_quote_id") and r.json()["new_quote_id"] != pre_repair["quote_id"]:
            _track(r.json()["new_quote_id"])
        assert r.status_code == 200, f"Modificar ({mode}) bloqueado: {r.status_code} {r.text[:200]}"
        assert r.json()["new_quote_number"].startswith("PRE-"), r.json()


# --- Envío por correo ---
class TestSendPreliminary:
    def test_invalid_email(self, H, pre_repair):
        r = requests.post(f"{BASE_URL}/api/quotes/{pre_repair['quote_id']}/send-preliminary", headers=H,
                          json={"email": "no-es-correo"}, timeout=30)
        assert r.status_code == 422

    def test_valid_email(self, H, pre_repair):
        r = requests.post(f"{BASE_URL}/api/quotes/{pre_repair['quote_id']}/send-preliminary", headers=H,
                          json={"email": "rgonzalez@megasoft.com.ve"}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["message"] == "Cotización preliminar enviada exitosamente a rgonzalez@megasoft.com.ve"


# --- Asignación de cliente ---
class TestAssign:
    def test_assign_rejects_sin_rif(self, H, pre_repair):
        r = requests.post(f"{BASE_URL}/api/quotes/{pre_repair['quote_id']}/assign-client", headers=H,
                          json={"client_id": SIN_RIF}, timeout=30)
        assert r.status_code == 400

    def test_assign_flow(self, H, real_client):
        pre = _vpos(H, SIN_RIF)
        r = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/assign-client", headers=H,
                          json={"client_id": real_client["client_id"]}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert COT_RE.match(d["quote_number"]) and d["preliminary_number"] == pre["quote_number"]
        q = requests.get(f"{BASE_URL}/api/quotes/{pre['quote_id']}", headers=H, timeout=30).json()
        assert q["quote_number"] == d["quote_number"] and q["client_id"] == real_client["client_id"]
        # segunda asignación
        r2 = requests.post(f"{BASE_URL}/api/quotes/{pre['quote_id']}/assign-client", headers=H,
                           json={"client_id": real_client["client_id"]}, timeout=30)
        assert r2.status_code == 400 and "no es preliminar" in r2.json()["detail"]
        # acciones liberadas: pdf ya no devuelve el mensaje PRE
        r3 = requests.get(f"{BASE_URL}/api/quotes/{pre['quote_id']}/pdf", headers=H, timeout=60)
        assert not (r3.status_code == 400 and r3.json().get("detail") == PRE_MSG)
