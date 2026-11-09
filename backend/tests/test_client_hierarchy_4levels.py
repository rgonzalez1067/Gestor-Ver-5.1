# Jerarquía de clientes en 4 niveles: Grupo → Marca → RIF → Sucursal (herencia, drill-down, CRUD Marcas)
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"
SFX = uuid.uuid4().hex[:5].upper()


def _rif():
    return "J99" + str(uuid.uuid4().int)[:7]


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
    created = {"clients": [], "brands": [], "groups": []}
    t = {}
    try:
        g = s.post(f"{API}/grupos-economicos", json={
            "name": f"QA4N Grupo {SFX}", "contacts": [{"full_name": "Corp A", "email": "corpa@qa4n.com"}],
            "characteristics": {"segment": "Corporativo", "categoria_comercial": "Retail"}})
        assert g.status_code == 200, g.text
        g = g.json(); created["groups"].append(g["group_id"]); t["g"] = g
        ba = s.post(f"{API}/marcas", json={"name": f"QA4N Marca A {SFX}", "group_id": g["group_id"]}).json()
        created["brands"].append(ba["brand_id"]); t["ba"] = ba
        bb = s.post(f"{API}/marcas", json={"name": f"QA4N Marca B {SFX}", "group_id": g["group_id"],
                                            "contacts": [{"full_name": "Marca B", "email": "mb@qa4n.com"}],
                                            "characteristics": {"segment": "Pymes"}}).json()
        created["brands"].append(bb["brand_id"]); t["bb"] = bb
        rifs = []
        for i, b in enumerate((ba, ba, bb)):
            r = s.post(f"{API}/clients", json={"rif": _rif(), "legal_name": f"QA4N RIF {i} {SFX} CA",
                                               "marca_id": b["brand_id"], "grupo_economico_id": g["group_id"],
                                               "segment": "Pymes" if b is bb else "Corporativo"})
            assert r.status_code == 200, r.text
            rifs.append(r.json()); created["clients"].append(r.json()["client_id"])
        t["a1"], t["a2"], t["b1"] = rifs
        brs = []
        for n in ("S1", "S2", "S3"):
            body = {"sucursal": f"{n}"}
            if n == "S3":
                body["contacts"] = [{"full_name": "Local C", "email": "lc@qa4n.com"}]
            r = s.post(f"{API}/clients/{t['a1']['client_id']}/branches", json=body)
            assert r.status_code == 200, r.text
        lst = s.get(f"{API}/clients/{t['a1']['client_id']}/branches").json()["branches"]
        for b in lst:
            created["clients"].append(b["client_id"])
        t["branches"] = sorted(lst, key=lambda x: x["sucursal"])
        t["created"] = created
        yield t
    finally:
        for cid in reversed(created["clients"]):
            s.delete(f"{API}/clients/{cid}")
        for bid in created["brands"]:
            s.delete(f"{API}/marcas/{bid}")
        for gid in created["groups"]:
            s.delete(f"{API}/grupos-economicos/{gid}")


class TestDrillDown:
    def test_group_brands(self, s, tree):
        r = s.get(f"{API}/grupos-economicos/{tree['g']['group_id']}/marcas").json()
        names = sorted(b["name"] for b in r)
        assert names == sorted([tree["ba"]["name"], tree["bb"]["name"]])
        a = next(b for b in r if b["brand_id"] == tree["ba"]["brand_id"])
        assert a["rif_count"] == 2

    def test_brand_rifs(self, s, tree):
        r = s.get(f"{API}/marcas/{tree['ba']['brand_id']}/rifs").json()
        assert len(r) == 2
        assert {x["rif"] for x in r} == {tree["a1"]["rif"], tree["a2"]["rif"]}
        a1 = next(x for x in r if x["client_id"] == tree["a1"]["client_id"])
        assert a1["branches_count"] == 3 and a1["legal_name"].startswith("QA4N")

    def test_branches(self, s, tree):
        assert [b["sucursal"] for b in tree["branches"]] == ["S1", "S2", "S3"]
        for b in tree["branches"]:
            d = s.get(f"{API}/clients/{b['client_id']}").json()
            assert d["marca_id"] == tree["ba"]["brand_id"] and d["grupo_economico_id"] == tree["g"]["group_id"]

    def test_group_brands_count(self, s, tree):
        g = s.get(f"{API}/grupos-economicos/{tree['g']['group_id']}").json()
        assert g["brands_count"] == 2

    def test_brand_group_filter(self, s, tree):
        r = s.get(f"{API}/marcas", params={"group_id": tree["g"]["group_id"]}).json()
        assert len(r) == 2


class TestCreateRules:
    def test_group_without_brand_400(self, s, tree):
        r = s.post(f"{API}/clients", json={"rif": _rif(), "legal_name": "QA4N NOBRAND", "grupo_economico_id": tree["g"]["group_id"]})
        assert r.status_code == 400
        assert "debe indicar la Marca" in r.json()["detail"]

    def test_standalone_rif(self, s, tree):
        r = s.post(f"{API}/clients", json={"rif": _rif(), "legal_name": f"QA4N SOLO {SFX}"})
        assert r.status_code == 200, r.text
        c = r.json(); tree["created"]["clients"].append(c["client_id"])
        assert c.get("marca_id") in (None, "") and c.get("grupo_economico_id") in (None, "")
        assert c["fantasy_name"] == f"QA4N SOLO {SFX}"

    def test_rif_inherits_brand_fantasy_and_group(self, tree):
        a1 = tree["a1"]
        assert a1["fantasy_name"] == tree["ba"]["name"]
        assert a1["grupo_economico_id"] == tree["g"]["group_id"]
        assert a1["segment"] == "Corporativo" and a1["categoria_comercial"] == "Retail"
        assert tree["b1"]["segment"] == "Pymes"


class TestDefaultSegment:
    def test_api_omitted_segment_inherits_group(self, s, tree):
        # ClientCreate.segment defaults to 'Pymes' -> omitted segment is treated as a local override
        r = s.post(f"{API}/clients", json={"rif": _rif(), "legal_name": f"QA4N DEFSEG {SFX}",
                                           "marca_id": tree["ba"]["brand_id"], "grupo_economico_id": tree["g"]["group_id"]})
        assert r.status_code == 200, r.text
        c = r.json(); tree["created"]["clients"].append(c["client_id"])
        assert c["segment"] == "Corporativo", f"segment={c['segment']} overrides={c['inherit_overrides']}"


class TestContactsInheritance:
    def _cc(self, s, cid):
        return [(x["scope"], x["email"], x["effective"]) for x in s.get(f"{API}/clients/{cid}/consolidated-contacts").json()["contacts"]]

    def test_rif_brand_a_inherits_group(self, s, tree):
        cc = self._cc(s, tree["a2"]["client_id"])
        assert ("grupo", "corpa@qa4n.com", True) in cc

    def test_rif_brand_b_uses_brand(self, s, tree):
        cc = self._cc(s, tree["b1"]["client_id"])
        assert ("marca", "mb@qa4n.com", True) in cc
        assert ("grupo", "corpa@qa4n.com", False) in cc

    def test_branch_local_only(self, s, tree):
        cc = self._cc(s, tree["branches"][2]["client_id"])
        eff = [c for c in cc if c[2]]
        assert eff == [("local", "lc@qa4n.com", True)]
        cc0 = self._cc(s, tree["branches"][0]["client_id"])
        assert ("grupo", "corpa@qa4n.com", True) in cc0


class TestCharacteristicsInheritance:
    def test_group_change_propagates(self, s, tree):
        g = tree["g"]
        r = s.put(f"{API}/grupos-economicos/{g['group_id']}", json={
            "name": g["name"], "contacts": [{"full_name": "Corp A", "email": "corpa@qa4n.com"}],
            "characteristics": {"segment": "Corporativo", "categoria_comercial": "Farmacias"}})
        assert r.status_code == 200, r.text
        assert s.get(f"{API}/clients/{tree['a1']['client_id']}").json()["categoria_comercial"] == "Farmacias"
        assert s.get(f"{API}/clients/{tree['branches'][0]['client_id']}").json()["categoria_comercial"] == "Farmacias"
        b1 = s.get(f"{API}/clients/{tree['b1']['client_id']}").json()
        assert b1["segment"] == "Pymes" and b1["categoria_comercial"] == "Farmacias"

    def test_inheritance_source_levels(self, s, tree):
        inh = s.get(f"{API}/clients/{tree['branches'][0]['client_id']}/inheritance").json()
        src = {x["field"]: x["source_level"] for x in inh["characteristics"]}
        assert src["segment"] == "grupo" and src["categoria_comercial"] == "grupo"
        inhb = s.get(f"{API}/clients/{tree['b1']['client_id']}/inheritance").json()
        srcb = {x["field"]: x["source_level"] for x in inhb["characteristics"]}
        assert srcb["segment"] == "marca"
        assert [l["scope"] for l in inh["levels"]] == ["local", "principal", "marca", "grupo"]

    def test_local_override_survives_propagation(self, s, tree):
        br = s.get(f"{API}/clients/{tree['branches'][1]['client_id']}").json()
        br["categoria_comercial"] = "Restaurantes"
        r = s.put(f"{API}/clients/{br['client_id']}", json=br)
        assert r.status_code == 200, r.text
        assert "categoria_comercial" in r.json()["inherit_overrides"]
        g = tree["g"]
        s.put(f"{API}/grupos-economicos/{g['group_id']}", json={
            "name": g["name"], "contacts": [{"full_name": "Corp A", "email": "corpa@qa4n.com"}],
            "characteristics": {"segment": "Corporativo", "categoria_comercial": "Hoteles"}})
        assert s.get(f"{API}/clients/{br['client_id']}").json()["categoria_comercial"] == "Restaurantes"
        assert s.get(f"{API}/clients/{tree['a1']['client_id']}").json()["categoria_comercial"] == "Hoteles"
        inh = s.get(f"{API}/clients/{br['client_id']}/inheritance").json()
        assert {x["field"]: x["source_level"] for x in inh["characteristics"]}["categoria_comercial"] == "local"


class TestBrandCRUD:
    def test_duplicate_name_400(self, s, tree):
        r = s.post(f"{API}/marcas", json={"name": tree["ba"]["name"].lower()})
        assert r.status_code == 400

    def test_delete_with_rifs_400(self, s, tree):
        r = s.delete(f"{API}/marcas/{tree['ba']['brand_id']}")
        assert r.status_code == 400

    def test_rename_updates_fantasy(self, s, tree):
        b = tree["bb"]
        new = f"QA4N Marca B2 {SFX}"
        r = s.put(f"{API}/marcas/{b['brand_id']}", json={"name": new, "group_id": tree["g"]["group_id"],
                                                         "contacts": b.get("contacts", []), "characteristics": {"segment": "Pymes"}})
        assert r.status_code == 200, r.text
        assert s.get(f"{API}/clients/{tree['b1']['client_id']}").json()["fantasy_name"] == new
        tree["bb"]["name"] = new

    def test_create_edit_delete(self, s):
        r = s.post(f"{API}/marcas", json={"name": f"TEST_QA4N Temp {SFX}"})
        assert r.status_code == 200
        bid = r.json()["brand_id"]
        assert s.put(f"{API}/marcas/{bid}", json={"name": f"TEST_QA4N Temp2 {SFX}"}).json()["name"] == f"TEST_QA4N Temp2 {SFX}"
        assert s.delete(f"{API}/marcas/{bid}").status_code == 200
        assert s.get(f"{API}/marcas/{bid}").status_code == 404


class TestRegression:
    def test_put_existing_client_with_brand(self, s, tree):
        c = s.get(f"{API}/clients/{tree['a2']['client_id']}").json()
        c["legal_name"] = c["legal_name"] + " MOD"
        r = s.put(f"{API}/clients/{c['client_id']}", json=c)
        assert r.status_code == 200, r.text
        assert r.json()["marca_id"] == tree["ba"]["brand_id"] and r.json()["legal_name"].endswith("MOD")
