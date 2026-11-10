# Orden de estructura del alcance (Marca A-Z, sin marca al final → RIF A-Z → Principal primero, sucursales A-Z)
# en cotización (scope_tree/cotizacion_sucursales), proyecto (rifs/stores), to_distribution y Matriz_Alcance_Cotizacion
import os
import sys
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]).rstrip("/")
API = f"{BASE_URL}/api"
SFX = uuid.uuid4().hex[:5].upper()
CREATED = {"clients": [], "brands": [], "groups": [], "quotes": []}
sys.path.insert(0, "/app/backend")


def _rif():
    return "J96" + str(uuid.uuid4().int)[:7]


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    if r.status_code != 200 or "session_token" not in r.json():
        pytest.skip(f"login failed {r.status_code}")
    ses.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    return ses


@pytest.fixture(scope="module")
def t(s):
    t = {}
    try:
        g = s.post(f"{API}/grupos-economicos", json={"name": f"TEST_ORD Grupo {SFX}"}).json()
        CREATED["groups"].append(g["group_id"]); t["g"] = g
        # crear marca Zeta primero (orden de creación != alfabético)
        for k, name in (("Z", "Zeta"), ("A", "Alfa")):
            b = s.post(f"{API}/marcas", json={"name": f"TEST_ORD {name} {SFX}", "group_id": g["group_id"]}).json()
            CREATED["brands"].append(b["brand_id"]); t["b" + k] = b
        # RIFs: Alfa → "Mango", "Banana"; Zeta → "Kiwi", "Coco"; sin marca → "Aaa Nomarca"
        for key, legal, br in (("aM", "Mango", "bA"), ("aB", "Banana", "bA"), ("zK", "Kiwi", "bZ"), ("zC", "Coco", "bZ"), ("nm", "Aaa Nomarca", None)):
            body = {"rif": _rif(), "legal_name": f"TEST_ORD {legal} {SFX} CA"}
            if br:
                body["marca_id"] = t[br]["brand_id"]
                body["grupo_economico_id"] = g["group_id"]
            r = s.post(f"{API}/clients", json=body)
            assert r.status_code == 200, r.text
            CREATED["clients"].append(r.json()["client_id"]); t[key] = r.json()
        for n in ("Zulia", "Barinas"):
            r = s.post(f"{API}/clients/{t['aB']['client_id']}/branches", json={"sucursal": f"TEST_ORD {n}"})
            assert r.status_code == 200, r.text
        br = s.get(f"{API}/clients/{t['aB']['client_id']}/branches").json()
        t["brs"] = br["branches"]
        for b in br["branches"]:
            CREATED["clients"].append(b["client_id"])
        yield t
    finally:
        projs = s.get(f"{API}/projects", params={"limit": 1000}).json()
        projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
        for p in projs:
            if p.get("quote_id") in CREATED["quotes"]:
                s.delete(f"{API}/projects/{p['project_id']}")
        for q in CREATED["quotes"]:
            s.delete(f"{API}/quotes/{q}")
            s.delete(f"{API}/quote-history/qhist_{q}")
        for c in reversed(CREATED["clients"]):
            s.delete(f"{API}/clients/{c}")
        for bid in CREATED["brands"]:
            s.delete(f"{API}/marcas/{bid}")
        for gid in CREATED["groups"]:
            s.delete(f"{API}/grupos-economicos/{gid}")


def _node(t, key, brand_key, stores):
    r = t[key]
    b = t[brand_key] if brand_key else {}
    return {"client_id": r["client_id"], "rif": r["rif"], "legal_name": r["legal_name"], "marca_id": b.get("brand_id"),
            "marca_name": b.get("name") or "", "stores": stores}


def _principal(t, key, boxes):
    return {"client_id": t[key]["client_id"], "name": "Principal", "is_principal": True, "boxes": boxes}


def _messy_tree(t):
    by = {b["sucursal"]: b for b in t["brs"]}
    banana_stores = [  # reversed: Zulia, Barinas, Principal(last)
        {"client_id": by[f"TEST_ORD Zulia"]["client_id"], "name": "TEST_ORD Zulia", "is_principal": False, "boxes": 3},
        {"client_id": by[f"TEST_ORD Barinas"]["client_id"], "name": "TEST_ORD Barinas", "is_principal": False, "boxes": 2},
        _principal(t, "aB", 1),
    ]
    return [
        _node(t, "nm", None, [_principal(t, "nm", 1)]),
        _node(t, "zK", "bZ", [_principal(t, "zK", 4)]),
        _node(t, "aM", "bA", [_principal(t, "aM", 5)]),
        _node(t, "zC", "bZ", [_principal(t, "zC", 6)]),
        _node(t, "aB", "bA", banana_stores),
    ]


EXPECTED_RIFS = ["aB", "aM", "zC", "zK", "nm"]  # Alfa(Banana, Mango) → Zeta(Coco, Kiwi) → sin marca
EXPECTED_STORES_B = ["Principal", "TEST_ORD Barinas", "TEST_ORD Zulia"]


def _create(s, t, tree):
    body = {"client_id": t["aB"]["client_id"], "quote_type": "VPOS", "quote_category": "implementation", "notes": f"TEST_ORD {SFX}",
            "cantidad_cajas": 22, "nivel_cotizacion": "GRUPO", "grupo_economico_id": t["g"]["group_id"],
            "grupo_economico_name": t["g"]["name"], "scope_tree": tree, "cajas_desglose": True, "patrocinador_tipo": "CLIENTE",
            "sponsored_implementation": False,
            "services": [{"item_type": "service", "item_id": "svc_test", "item_name": "TEST_ORD Servicio", "quantity": 1, "unit_price_usd": 100, "total_usd": 100}]}
    r = s.post(f"{API}/quotes/create-with-pdf", json=body)
    assert r.status_code == 200, r.text[:300]
    qid = r.json().get("quote_id") or (r.json().get("quote") or {}).get("quote_id")
    CREATED["quotes"].append(qid)
    return qid


class TestScopeOrder:
    def test_quote_scope_tree_sorted(self, s, t):
        qid = _create(s, t, _messy_tree(t))
        t["qid"] = qid
        q = s.get(f"{API}/quotes/{qid}").json()
        assert [r["client_id"] for r in q["scope_tree"]] == [t[k]["client_id"] for k in EXPECTED_RIFS]
        assert [st["name"] for st in q["scope_tree"][0]["stores"]] == EXPECTED_STORES_B
        assert q["scope_tree"][0]["stores"][0]["is_principal"] is True
        assert q["tipo_proyecto_inferido"] == "Multi Marca"

    def test_cotizacion_sucursales_order(self, s, t):
        q = s.get(f"{API}/quotes/{t['qid']}").json()
        cs = q["cotizacion_sucursales"]
        assert len(cs) == 7
        rif_seq = []
        for x in cs:
            if not rif_seq or rif_seq[-1] != x["rif_client_id"]:
                rif_seq.append(x["rif_client_id"])
        assert rif_seq == [t[k]["client_id"] for k in EXPECTED_RIFS]
        assert [x["sucursal"] for x in cs[:3]] == EXPECTED_STORES_B
        assert [x["cajas"] for x in cs] == [1, 2, 3, 5, 6, 4, 1]

    def test_send_to_impl_project_order(self, s, t):
        qid = t["qid"]
        for st in ("Enviada", "Aprobada", "Facturada", "Pagada"):
            assert s.put(f"{API}/quotes/{qid}/status", json={"new_status": st}).status_code == 200
        r = s.post(f"{API}/quotes/{qid}/send-to-implementation", json={"project_type_impl": "vpos_mpos", "server_name": "TEST_ORD srv",
                                                                       "economic_group": "TEST_ORD", "fantasy_name": "TEST_ORD", "fiscal_printer_model": "TEST_ORD FP"})
        assert r.status_code == 200, r.text[:300]
        projs = s.get(f"{API}/projects", params={"limit": 1000}).json()
        projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
        p = next((x for x in projs if x.get("quote_id") == qid), None)
        assert p, "project not created"
        p = s.get(f"{API}/projects/{p['project_id']}").json()
        assert p["project_type"] == "multirif"
        assert [r["client_id"] for r in p["rifs"]] == [t[k]["client_id"] for k in EXPECTED_RIFS]
        assert [r["box_count"] for r in p["rifs"]] == [6, 5, 6, 4, 1]
        marcas = [st.get("marca_name") or "" for st in p["stores"]]
        assert marcas == [t["bA"]["name"]] * 4 + [t["bZ"]["name"]] * 2 + [""]
        assert [st["name"] for st in p["stores"][:3]] == EXPECTED_STORES_B
        assert [r["client_id"] for r in p["scope_tree"]] == [t[k]["client_id"] for k in EXPECTED_RIFS]


class TestUnitOrder:
    def test_to_distribution_and_vars(self, t):
        from services.quote_scope import to_distribution, scope_template_vars
        tree = _messy_tree(t)
        d = to_distribution(tree, True)
        assert [x["client_id"] for x in d] == [t[k]["client_id"] for k in EXPECTED_RIFS]
        assert [x["name"] for x in d[0]["stores"]] == EXPECTED_STORES_B
        v = scope_template_vars({"scope_tree": _messy_tree(t), "cajas_desglose": True})
        html = v["Matriz_Alcance_Cotizacion"]
        pos = [html.find(t[k]["legal_name"]) for k in EXPECTED_RIFS]
        assert all(p > 0 for p in pos) and pos == sorted(pos)
        assert html.find("Principal") < html.find("TEST_ORD Barinas") < html.find("TEST_ORD Zulia")
        assert v["Sucursales_Cotizacion"].startswith("Principal, TEST_ORD Barinas, TEST_ORD Zulia")
        assert v["RIFs_Cotizacion"].index(t["aB"]["legal_name"]) < v["RIFs_Cotizacion"].index(t["zK"]["legal_name"])
