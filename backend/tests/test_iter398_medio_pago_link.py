# Productos para Integración: medio_pago_id link + /links + audit; PDF pending concept
import os, time, requests, pytest
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env'); load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


@pytest.fixture(scope="module")
def s():
    r = requests.post(f"{API}/auth/login", json={"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"})
    assert r.status_code == 200, r.text
    tok = r.json().get("session_token") or r.json().get("token")
    se = requests.Session(); se.headers["Authorization"] = f"Bearer {tok}"
    return se


@pytest.fixture(scope="module")
def c2p_id(s):
    svcs = s.get(f"{API}/services").json()
    m = [x for x in svcs if x.get("name", "").strip().lower() == "pago c2p"]
    assert m, "Pago C2P service not found"
    return m[0]["service_id"]


@pytest.fixture(scope="module")
def original(s):
    d = next(p for p in s.get(f"{API}/productos-integracion").json() if p["producto_id"] == "prod_c2p")
    yield d
    s.put(f"{API}/productos-integracion/prod_c2p", json={"medio_pago_id": d.get("medio_pago_id")})


def test_link_and_list(s, c2p_id, original):
    t0 = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
    r = s.put(f"{API}/productos-integracion/prod_c2p", json={"medio_pago_id": c2p_id})
    assert r.status_code == 200, r.text
    assert r.json()["medio_pago_id"] == c2p_id
    p = next(p for p in s.get(f"{API}/productos-integracion").json() if p["producto_id"] == "prod_c2p")
    assert p["medio_pago_name"].lower() == "pago c2p"
    links = s.get(f"{API}/productos-integracion/links").json()
    assert any(l["producto_id"] == "prod_c2p" and l["medio_pago_id"] == c2p_id and l["medio_pago_name"] for l in links)
    time.sleep(1.5)
    a = list(db.audit_trails.find({"modulo": "Productos para Integración"}, {"_id": 0}).sort([("_id", -1)]).limit(3))
    print(a[:1])
    assert a and any("UPDATE" in str(x.get("accion", x.get("action", ""))).upper() for x in a)


def test_invalid_medio_pago(s, original):
    r = s.put(f"{API}/productos-integracion/prod_c2p", json={"medio_pago_id": "svc_nonexistent_xyz"})
    assert r.status_code == 400
    assert "Medio de Pago" in r.json()["detail"]


def test_links_requires_auth():
    assert requests.get(f"{API}/productos-integracion/links").status_code in (401, 403)


def test_unlink_null(s, c2p_id, original):
    s.put(f"{API}/productos-integracion/prod_c2p", json={"medio_pago_id": c2p_id})
    r = s.put(f"{API}/productos-integracion/prod_c2p", json={"medio_pago_id": None})
    assert r.status_code == 200 and r.json()["medio_pago_id"] is None
    links = s.get(f"{API}/productos-integracion/links").json()
    assert not any(l["producto_id"] == "prod_c2p" for l in links)
