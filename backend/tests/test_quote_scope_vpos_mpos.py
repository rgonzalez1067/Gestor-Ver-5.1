# Alcance jerárquico VPOS/MPOS (Grupo→Marcas→RIFs→Sucursales), tipificación, patrocinio, proyecto y variables
import os
import sys
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]).rstrip("/")
API = f"{BASE_URL}/api"
SFX = uuid.uuid4().hex[:5].upper()
CREATED = {"clients": [], "brands": [], "groups": [], "quotes": [], "projects": [], "history": []}


def _rif():
    return "J98" + str(uuid.uuid4().int)[:7]


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    if r.status_code != 200 or "session_token" not in r.json():
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    ses.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    return ses


@pytest.fixture(scope="module")
def tree(s):
    t = {}
    try:
        g = s.post(f"{API}/grupos-economicos", json={"name": f"TEST_QS Grupo {SFX}"})
        assert g.status_code == 200, g.text
        t["g"] = g.json(); CREATED["groups"].append(t["g"]["group_id"])
        for k in ("A", "B"):
            b = s.post(f"{API}/marcas", json={"name": f"TEST_QS Marca {k} {SFX}", "group_id": t["g"]["group_id"]})
            assert b.status_code == 200, b.text
            t[f"b{k}"] = b.json(); CREATED["brands"].append(b.json()["brand_id"])
        for k in ("A", "B"):
            r = s.post(f"{API}/clients", json={"rif": _rif(), "legal_name": f"TEST_QS RIF {k} {SFX} CA",
                                               "marca_id": t[f"b{k}"]["brand_id"], "grupo_economico_id": t["g"]["group_id"]})
            assert r.status_code == 200, r.text
            t[f"r{k}"] = r.json(); CREATED["clients"].append(r.json()["client_id"])
        # RIF A: 2 sucursales adicionales (principal + S1 + S2 = 3 tiendas)
        for n in ("S1", "S2"):
            r = s.post(f"{API}/clients/{t['rA']['client_id']}/branches", json={"sucursal": f"TEST_QS {n}"})
            assert r.status_code == 200, r.text
        br = s.get(f"{API}/clients/{t['rA']['client_id']}/branches").json()
        t["brA"] = br
        for b in br["branches"]:
            CREATED["clients"].append(b["client_id"])
        yield t
    finally:
        for pid in CREATED["projects"]:
            s.delete(f"{API}/projects/{pid}")
        for qid in CREATED["quotes"]:
            s.delete(f"{API}/quotes/{qid}")
        for hid in CREATED["history"]:
            s.delete(f"{API}/quote-history/{hid}")
        for cid in reversed(CREATED["clients"]):
            s.delete(f"{API}/clients/{cid}")
        for bid in CREATED["brands"]:
            s.delete(f"{API}/marcas/{bid}")
        for gid in CREATED["groups"]:
            s.delete(f"{API}/grupos-economicos/{gid}")


def _stores_a(t, boxes=(2, 3, 5)):
    p = t["brA"]["principal"]
    sts = [{"client_id": p.get("client_id") or t["rA"]["client_id"], "name": p.get("sucursal") or "Principal", "is_principal": True}]
    sts += [{"client_id": b["client_id"], "name": b["sucursal"], "is_principal": False} for b in t["brA"]["branches"]]
    return [dict(x, boxes=n) for x, n in zip(sts, boxes)]


def _scope_tree(t, two_brands=True):
    tr = [{"client_id": t["rA"]["client_id"], "rif": t["rA"]["rif"], "legal_name": t["rA"]["legal_name"],
           "marca_id": t["bA"]["brand_id"], "marca_name": t["bA"]["name"], "stores": _stores_a(t)}]
    if two_brands:
        tr.append({"client_id": t["rB"]["client_id"], "rif": t["rB"]["rif"], "legal_name": t["rB"]["legal_name"],
                   "marca_id": t["bB"]["brand_id"], "marca_name": t["bB"]["name"],
                   "stores": [{"client_id": t["rB"]["client_id"], "name": "Principal", "is_principal": True, "boxes": 4}]})
    return tr


def _create(s, t, scope_tree, extra=None):
    body = {"client_id": t["rA"]["client_id"], "quote_type": "VPOS", "quote_category": "implementation",
            "notes": f"TEST_QS {SFX}", "cantidad_cajas": 14,
            "nivel_cotizacion": "GRUPO", "grupo_economico_id": t["g"]["group_id"], "grupo_economico_name": t["g"]["name"],
            "scope_tree": scope_tree, "cajas_desglose": True,
            "patrocinador_tipo": "CLIENTE", "patrocinador_id": t["rB"]["client_id"], "patrocinador_nombre": t["rB"]["legal_name"],
            "services": [{"item_type": "service", "item_id": "svc_test", "item_name": "TEST_QS Servicio", "quantity": 1, "unit_price_usd": 100, "total_usd": 100}]}
    body.update(extra or {})
    r = s.post(f"{API}/quotes/create-with-pdf", json=body)
    assert r.status_code == 200, r.text[:500]
    d = r.json()
    qid = d.get("quote_id") or (d.get("quote") or {}).get("quote_id")
    assert qid, d
    CREATED["quotes"].append(qid)
    return qid


class TestScopePersistence:
    def test_cascade_endpoints(self, s, tree):
        gs = s.get(f"{API}/grupos-economicos").json()
        assert any(g["group_id"] == tree["g"]["group_id"] for g in gs)
        ms = [m for m in s.get(f"{API}/marcas").json() if m.get("group_id") == tree["g"]["group_id"]]
        assert len(ms) == 2
        rifs = s.get(f"{API}/marcas/{tree['bA']['brand_id']}/rifs").json()
        assert [r["client_id"] for r in rifs] == [tree["rA"]["client_id"]]
        assert len(tree["brA"]["branches"]) == 2

    def test_create_multimarca(self, s, tree):
        qid = _create(s, tree, _scope_tree(tree))
        q = s.get(f"{API}/quotes/{qid}").json()
        assert q["nivel_cotizacion"] == "GRUPO"
        assert q["grupo_economico_id"] == tree["g"]["group_id"]
        assert len(q["scope_tree"]) == 2
        assert q["cajas_desglose"] is True
        assert q["patrocinador_tipo"] == "CLIENTE"
        assert q["patrocinador_id"] == tree["rB"]["client_id"]
        assert q["patrocinador_nombre"] == tree["rB"]["legal_name"]
        assert q["tipo_proyecto_inferido"] == "Multi Marca"
        assert len(q["cotizacion_sucursales"]) == 4
        assert sum(x["cajas"] for x in q["cotizacion_sucursales"]) == 14
        tree["q_mm"] = qid

    def test_put_recalculates(self, s, tree):
        qid = tree["q_mm"]
        one = _scope_tree(tree, two_brands=False)
        r = s.put(f"{API}/quotes/{qid}", json={"scope_tree": one, "cajas_desglose": True, "patrocinador_tipo": "CLIENTE",
                                              "patrocinador_id": tree["rA"]["client_id"], "patrocinador_nombre": "X"})
        assert r.status_code == 200, r.text[:300]
        q = s.get(f"{API}/quotes/{qid}").json()
        assert q["tipo_proyecto_inferido"] == "Multitienda"
        assert len(q["cotizacion_sucursales"]) == 3
        one[0]["stores"] = one[0]["stores"][:1]
        s.put(f"{API}/quotes/{qid}", json={"scope_tree": one, "cajas_desglose": True, "patrocinador_tipo": "CLIENTE"})
        assert s.get(f"{API}/quotes/{qid}").json()["tipo_proyecto_inferido"] == "Monotienda"
        r2 = [_scope_tree(tree, False)[0], dict(_scope_tree(tree, False)[0], client_id=tree["rB"]["client_id"], stores=[{"client_id": tree["rB"]["client_id"], "name": "P"}])]
        s.put(f"{API}/quotes/{qid}", json={"scope_tree": r2, "cajas_desglose": True, "patrocinador_tipo": "CLIENTE"})
        assert s.get(f"{API}/quotes/{qid}").json()["tipo_proyecto_inferido"] == "Multi RIF"

    def test_put_partial_scope_preserves_sponsor(self, s, tree):
        """PUT con sólo scope_tree no debería borrar patrocinador_tipo/cajas_desglose."""
        qid = tree["q_mm"]
        s.put(f"{API}/quotes/{qid}", json={"scope_tree": _scope_tree(tree), "cajas_desglose": True, "patrocinador_tipo": "CLIENTE"})
        s.put(f"{API}/quotes/{qid}", json={"scope_tree": _scope_tree(tree)})
        q = s.get(f"{API}/quotes/{qid}").json()
        assert q["tipo_proyecto_inferido"] == "Multi Marca"
        assert q.get("patrocinador_tipo") == "CLIENTE", f"patrocinador_tipo clobbered -> {q.get('patrocinador_tipo')}"
        assert q.get("cajas_desglose") is True, f"cajas_desglose clobbered -> {q.get('cajas_desglose')}"


class TestProject:
    def _to_project(self, s, qid):
        for st in ("Enviada", "Aprobada", "Facturada", "Pagada", "Enviada a Imple"):
            r = s.put(f"{API}/quotes/{qid}/status", json={"new_status": st})
            assert r.status_code == 200, f"{st}: {r.text[:300]}"
        CREATED["history"].append(f"qhist_{qid}")
        projs = s.get(f"{API}/projects", params={"limit": 500}).json()
        projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
        p = next((x for x in projs if x.get("quote_id") == qid), None)
        assert p, "project not found"
        CREATED["projects"].append(p["project_id"])
        return s.get(f"{API}/projects/{p['project_id']}").json()

    def test_multimarca_project(self, s, tree):
        qid = _create(s, tree, _scope_tree(tree), {"sponsored_implementation": False})
        p = self._to_project(s, qid)
        assert p["tipologia_proyecto"] == "Multi Marca"
        assert p["project_type"] == "multirif"
        assert len(p["rifs"]) == 2
        assert len(p["stores"]) == 4
        assert all(st.get("marca_name") for st in p["stores"])
        assert sum(st["box_count"] for st in p["stores"]) == 14
        tree["p_mm"] = p["project_id"]

    def test_multitienda_project(self, s, tree):
        qid = _create(s, tree, _scope_tree(tree, two_brands=False), {"nivel_cotizacion": "RIF"})
        q = s.get(f"{API}/quotes/{qid}").json()
        assert q["tipo_proyecto_inferido"] == "Multitienda"
        p = self._to_project(s, qid)
        assert p["tipologia_proyecto"] == "Multitienda"
        assert p["project_type"] == "multistore"
        assert len(p["stores"]) == 3
        assert sorted(st["box_count"] for st in p["stores"]) == [2, 3, 5]


class TestTemplateVars:
    def test_scope_template_vars(self, tree):
        sys.path.insert(0, "/app/backend")
        from services.quote_scope import scope_template_vars
        v = scope_template_vars({"nivel_cotizacion": "GRUPO", "scope_tree": _scope_tree(tree), "cajas_desglose": True,
                                 "tipo_proyecto_inferido": "Multi Marca", "patrocinador_tipo": "BANCO", "patrocinador_nombre": "Banco X"})
        assert v["Nivel_Cotizacion"] == "Grupo Económico"
        assert tree["bA"]["name"] in v["Marcas_Cotizacion"] and tree["bB"]["name"] in v["Marcas_Cotizacion"]
        assert v["Tipologia_Proyecto"] == "Multi Marca"
        assert v["Tipo_Patrocinio"] == "Patrocinada por Banco/Ente"
        assert v["Patrocinador_Cotizacion"] == "Banco X"
        assert v["Total_Cajas_Cotizacion"] == "14"
        assert "<table" in v["Matriz_Alcance_Cotizacion"]

    def test_vars_in_editor_lists(self):
        src = open("/app/frontend/src/components/email/templateVariables.js").read() + open("/app/frontend/src/components/EmailTemplatesEditor.jsx").read()
        for k in ("Nivel_Cotizacion", "Marcas_Cotizacion", "Tipologia_Proyecto", "Tipo_Patrocinio",
                  "Patrocinador_Cotizacion", "Total_Cajas_Cotizacion", "Matriz_Alcance_Cotizacion"):
            assert k in src, k
