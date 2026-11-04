# Iter 353: Servicio Express en cotizaciones (persistencia servicio_express + flags express/expressManual) y with_phase_tag Producción
import os
import sys
import pytest
import requests

sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"})
    if r.status_code != 200:
        pytest.skip("login failed")
    d = r.json()
    sess.headers.update({"Authorization": f"Bearer {d.get('session_token') or d.get('token')}"})
    return sess


@pytest.fixture(scope="module")
def client_id(s):
    data = s.get(f"{API}/clients?limit=1").json()
    data = data if isinstance(data, list) else data.get("clients", [])
    return data[0]["client_id"]


@pytest.fixture(scope="module")
def created(s):
    ids = {"quotes": [], "services": []}
    yield ids
    for q in ids["quotes"]:
        s.delete(f"{API}/quotes/{q}")
    for sid in ids["services"]:
        s.delete(f"{API}/services/{sid}")


def test_with_phase_tag_produccion_omitted():
    from models import with_phase_tag, QuotePDFItem
    assert with_phase_tag("X", "Producción") == "X"
    assert QuotePDFItem(concepto="Pago", operational_status="Producción").concepto == "Pago"
    assert with_phase_tag("X", "Primer Prod") == "X [Primer Prod]"


def test_catalog_service_fields(s, created):
    r = s.post(f"{API}/services", json={"name": "TEST_Servicio Express API", "service_type": "Servicio",
                                         "application_type": "setup", "setup_cost_conventional": 100,
                                         "setup_cost_outsourcing": 20})
    assert r.status_code in (200, 201), r.text
    d = r.json()
    created["services"].append(d["service_id"])
    assert d["setup_cost_conventional"] == 100 and d["setup_cost_outsourcing"] == 20


@pytest.mark.parametrize("qtype", ["VPOS", "MPOS"])
def test_quote_express_persist(s, client_id, created, qtype):
    payload = {
        "client_id": client_id, "quote_type": qtype, "notes": "TEST_express", "servicio_express": True,
        "cantidad_cajas": 3,
        "services": [
            {"item_type": "additional", "item_name": "Servicio Express", "quantity": 1, "unit_price_usd": 125,
             "total_usd": 125, "tarifa_setup": 125, "cantidad_cajas": 1, "cantidad_bancos": 1,
             "express": True, "expressManual": True, "lockBancos": True},
        ],
    }
    r = s.post(f"{API}/quotes", json=payload)
    assert r.status_code == 200, r.text[:300]
    qid = r.json()["quote_id"]
    created["quotes"].append(qid)
    g = s.get(f"{API}/quotes/{qid}").json()
    assert g.get("servicio_express") is True
    row = next(x for x in g["services"] if x["item_name"] == "Servicio Express")
    assert row["express"] is True and row["expressManual"] is True and row["tarifa_setup"] == 125
    # Update a No
    g["servicio_express"] = False
    u = s.put(f"{API}/quotes/{qid}", json={"client_id": g["client_id"], "quote_type": qtype,
                                            "services": [], "servicio_express": False, "notes": "TEST_express upd"})
    assert u.status_code == 200, u.text[:300]
    g2 = s.get(f"{API}/quotes/{qid}").json()
    assert g2.get("servicio_express") is False
