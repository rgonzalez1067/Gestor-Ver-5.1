# 'Enviar a Implementación' con alcance jerárquico (scope_tree): Multi RIF / Multi Marca / Monotienda vía POST /send-to-implementation (payload igual al del modal)
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]).rstrip("/")
API = f"{BASE_URL}/api"
SFX = uuid.uuid4().hex[:5].upper()
CREATED = {"clients": [], "brands": [], "groups": [], "quotes": []}


def _rif():
    return "J97" + str(uuid.uuid4().int)[:7]


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    if r.status_code != 200 or "session_token" not in r.json():
        pytest.skip(f"login failed {r.status_code}")
    ses.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    return ses


@pytest.fixture(scope="module")
def tree(s):
    t = {}
    try:
        g = s.post(f"{API}/grupos-economicos", json={"name": f"TEST_IMPL Grupo {SFX}"}).json()
        CREATED["groups"].append(g["group_id"]); t["g"] = g
        b = s.post(f"{API}/marcas", json={"name": f"TEST_IMPL Marca {SFX}", "group_id": g["group_id"]}).json()
        CREATED["brands"].append(b["brand_id"]); t["b"] = b
        b2 = s.post(f"{API}/marcas", json={"name": f"TEST_IMPL Marca2 {SFX}", "group_id": g["group_id"]}).json()
        CREATED["brands"].append(b2["brand_id"]); t["b2"] = b2
        for k, br in (("A", b), ("C", b), ("D", b2)):
            r = s.post(f"{API}/clients", json={"rif": _rif(), "legal_name": f"TEST_IMPL RIF {k} {SFX} CA",
                                               "marca_id": br["brand_id"], "grupo_economico_id": g["group_id"]}).json()
            CREATED["clients"].append(r["client_id"]); t[k] = r
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


def _node(t, k, brand, boxes):
    r = t[k]
    return {"client_id": r["client_id"], "rif": r["rif"], "legal_name": r["legal_name"], "marca_id": brand["brand_id"],
            "marca_name": brand["name"], "stores": [{"client_id": r["client_id"], "name": "Principal", "is_principal": True, "boxes": boxes}]}


def _paid_quote(s, t, scope_tree, cajas, nivel):
    body = {"client_id": t["A"]["client_id"], "quote_type": "VPOS", "quote_category": "implementation", "notes": f"TEST_IMPL {SFX}",
            "cantidad_cajas": cajas, "nivel_cotizacion": nivel, "grupo_economico_id": t["g"]["group_id"],
            "grupo_economico_name": t["g"]["name"], "scope_tree": scope_tree, "cajas_desglose": True, "patrocinador_tipo": "CLIENTE",
            "sponsored_implementation": False,
            "services": [{"item_type": "service", "item_id": "svc_test", "item_name": "TEST_IMPL Servicio", "quantity": 1, "unit_price_usd": 100, "total_usd": 100}]}
    r = s.post(f"{API}/quotes/create-with-pdf", json=body)
    assert r.status_code == 200, r.text[:300]
    qid = r.json().get("quote_id") or (r.json().get("quote") or {}).get("quote_id")
    CREATED["quotes"].append(qid)
    for st in ("Enviada", "Aprobada", "Facturada", "Pagada"):
        assert s.put(f"{API}/quotes/{qid}/status", json={"new_status": st}).status_code == 200
    return qid


def _send(s, qid):
    # mismo payload que el modal tras confirmScopeTree (sin stores planos)
    r = s.post(f"{API}/quotes/{qid}/send-to-implementation", json={"project_type_impl": "vpos_mpos", "server_name": "TEST_IMPL srv",
                                                                   "economic_group": "TEST_IMPL", "fantasy_name": "TEST_IMPL", "fiscal_printer_model": "TEST_IMPL FP"})
    assert r.status_code == 200, r.text[:300]
    projs = s.get(f"{API}/projects", params={"limit": 1000}).json()
    projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
    p = next((x for x in projs if x.get("quote_id") == qid), None)
    assert p, "project not created"
    return s.get(f"{API}/projects/{p['project_id']}").json()


class TestSendToImplScope:
    def test_multi_rif(self, s, tree):
        qid = _paid_quote(s, tree, [_node(tree, "A", tree["b"], 3), _node(tree, "C", tree["b"], 4)], 7, "MARCA")
        assert s.get(f"{API}/quotes/{qid}").json()["tipo_proyecto_inferido"] == "Multi RIF"
        p = _send(s, qid)
        assert p["tipologia_proyecto"] == "Multi RIF"
        assert p["project_type"] == "multirif"
        assert len(p["rifs"]) == 2 and sorted(r["box_count"] for r in p["rifs"]) == [3, 4]
        assert sum(st["box_count"] for st in p["stores"]) == 7
        assert p.get("fiscal_printer_model") == "TEST_IMPL FP"

    def test_multi_marca(self, s, tree):
        qid = _paid_quote(s, tree, [_node(tree, "A", tree["b"], 2), _node(tree, "D", tree["b2"], 6)], 8, "GRUPO")
        p = _send(s, qid)
        assert p["tipologia_proyecto"] == "Multi Marca"
        assert p["project_type"] == "multirif"
        assert {st["marca_name"] for st in p["stores"]} == {tree["b"]["name"], tree["b2"]["name"]}

    def test_monotienda_stays_single(self, s, tree):
        qid = _paid_quote(s, tree, [_node(tree, "A", tree["b"], 3)], 3, "RIF")
        assert s.get(f"{API}/quotes/{qid}").json()["tipo_proyecto_inferido"] == "Monotienda"
        p = _send(s, qid)
        assert p["tipologia_proyecto"] == "Monotienda"
        assert p["project_type"] not in ("multirif", "multistore")
