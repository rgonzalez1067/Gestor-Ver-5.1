# Multiproyectos API tests (iter 409): entities, search eligibility, preview, create, ficha técnica PDF
import os
import io
import pytest
import requests
from mp_fixture_iter409 import make_set, cleanup, db

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
EMAIL, PWD = "qa.integradores@megasoft.com.ve", "QaIntegr2026*Ok"


@pytest.fixture(scope="module")
def s():
    ss = requests.Session()
    r = ss.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PWD})
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    ss.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    return ss


@pytest.fixture(scope="module")
def data():
    d = make_set("API")
    A = d["_client"]("A", f"TEST_MARCA_A_{d['grupo'][-6:]}")
    B = d["_client"]("B", f"TEST_MARCA_B_{d['grupo'][-6:]}")
    d["A"], d["B"] = A, B
    d["qa"] = d["_quote"](A, "Aprobada", "qa", minutes=0)
    d["qb"] = d["_quote"](B, "Configurada", "qb", minutes=1)
    d["q_draft"] = d["_quote"](A, "Borrador", "draft", minutes=2)
    d["q_arch"] = d["_quote"](A, "Aprobada", "arch", {"archived": True}, minutes=3)
    d["q_sent"] = d["_quote"](A, "Aprobada", "sent", {"sent_to_implementation_at": "2026-01-01"}, minutes=4)
    d["q_linked"] = d["_quote"](B, "Pagada", "linked", minutes=5)
    db().proyecto_cotizaciones.insert_one({"proyecto_id": "prj_test_dummy_409", "cotizacion_id": d["q_linked"]})
    d["_serials"](d["qa"], A, 2)
    d["_serials"](d["qb"], B, 2)
    d["_serials"](d["qb"], B, 1, "asignado")
    d["_serials"](d["qb"], B, 1, "liberado")  # must NOT be counted
    d["projects"] = []
    yield d
    db().proyecto_cotizaciones.delete_many({"proyecto_id": "prj_test_dummy_409"})
    cleanup(d, d["projects"])


class TestEntities:
    def test_levels(self, s, data):
        for lvl in ("grupo", "marca", "rif"):
            r = s.get(f"{BASE_URL}/api/multiprojects/entities", params={"level": lvl})
            assert r.status_code == 200, r.text
            vals = [i["value"] for i in r.json()["items"]]
            exp = {"grupo": data["grupo"], "marca": f"TEST_MARCA_A_{data['grupo'][-6:]}", "rif": data["A"]}[lvl]
            assert exp in vals

    def test_invalid_level(self, s):
        assert s.get(f"{BASE_URL}/api/multiprojects/entities", params={"level": "xx"}).status_code == 400

    def test_no_auth(self):
        assert requests.get(f"{BASE_URL}/api/multiprojects/entities", params={"level": "grupo"}).status_code in (401, 403)


class TestFlow:
    def test_search_eligibility(self, s, data):
        r = s.get(f"{BASE_URL}/api/multiprojects/search", params={"level": "grupo", "value": data["grupo"]})
        assert r.status_code == 200, r.text
        qs = {q["quote_id"]: q for q in r.json()["quotes"]}
        assert set(qs) == {data["qa"], data["qb"]}, qs.keys()
        assert qs[data["qa"]]["equipment_count"] == 2
        assert qs[data["qb"]]["equipment_count"] == 3

    def test_search_by_marca_and_rif(self, s, data):
        r = s.get(f"{BASE_URL}/api/multiprojects/search", params={"level": "marca", "value": f"TEST_MARCA_B_{data['grupo'][-6:]}"})
        assert [q["quote_id"] for q in r.json()["quotes"]] == [data["qb"]]
        r = s.get(f"{BASE_URL}/api/multiprojects/search", params={"level": "rif", "value": data["A"]})
        assert [q["quote_id"] for q in r.json()["quotes"]] == [data["qa"]]

    def test_preview_requires_two(self, s, data):
        r = s.post(f"{BASE_URL}/api/multiprojects/preview", json={"quote_ids": [data["qa"]]})
        assert r.status_code == 400
        r = s.post(f"{BASE_URL}/api/multiprojects/preview", json={"quote_ids": [data["qa"], data["qa"]]})
        assert r.status_code == 400

    def test_preview_ineligible(self, s, data):
        r = s.post(f"{BASE_URL}/api/multiprojects/preview", json={"quote_ids": [data["qa"], data["q_draft"]]})
        assert r.status_code == 400

    def test_preview(self, s, data):
        r = s.post(f"{BASE_URL}/api/multiprojects/preview", json={"quote_ids": [data["qa"], data["qb"]]})
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["level"] == "Multi-Marca"
        assert p["total_equipments"] == 5
        by = {x["client_id"]: x for x in p["rifs"]}
        assert by[data["A"]]["equipment_count"] == 2 and by[data["B"]]["equipment_count"] == 3
        st = by[data["A"]]["stores"][0]
        assert st["quote_id"] == data["qa"] and len(st["equipments"]) == 2
        assert st["equipments"][0]["origen"] == "Almacen Torre Banco Plaza (Pymes)"

    def test_create(self, s, data):
        r = s.post(f"{BASE_URL}/api/multiprojects/create",
                   json={"quote_ids": [data["qa"], data["qb"]], "implementation_instructions": "TEST_instr"})
        assert r.status_code == 200, r.text
        pid = r.json()["project_id"]
        data["projects"].append(pid)
        data["pid"] = pid
        g = s.get(f"{BASE_URL}/api/projects/{pid}")
        assert g.status_code == 200, g.text
        pj = g.json().get("project", g.json())
        assert pj["is_multiproject"] is True
        assert pj["project_type"] == "multirif"
        assert len(pj["rifs"]) == 2 and len(pj["stores"]) == 2
        assert set(pj["quote_numbers"]) == {f"TEST-COT-API-qa-{data['grupo'][-6:]}", f"TEST-COT-API-qb-{data['grupo'][-6:]}"}
        by = {x["client_id"]: x for x in pj["equipments_by_rif"]}
        assert by[data["A"]]["equipment_count"] == 2 and by[data["B"]]["equipment_count"] == 3
        assert len(pj.get("equipments") or []) == 5
        assert pj.get("implementation_instructions") == "TEST_instr"

    def test_quotes_archived(self, s, data):
        for qid in (data["qa"], data["qb"]):
            q = db().quotes.find_one({"quote_id": qid})
            if q:
                assert q["quote_status"] == "Enviada a Imple" and q.get("archived") is True
            h = db().quote_history.find_one({"quote_id": qid})
            assert h and "Multiproyecto" in (h.get("multiproject_comment") or "")
            assert db().proyecto_cotizaciones.count_documents({"cotizacion_id": qid}) == 1
            sa = list(db().serial_assignments.find({"quote_id": qid, "status": {"$in": ["preasignado", "asignado"]}}))
            assert all(x.get("project_id") == data["pid"] for x in sa)

    def test_second_create_400_and_search_empty(self, s, data):
        r = s.post(f"{BASE_URL}/api/multiprojects/create", json={"quote_ids": [data["qa"], data["qb"]]})
        assert r.status_code == 400
        r = s.get(f"{BASE_URL}/api/multiprojects/search", params={"level": "grupo", "value": data["grupo"]})
        assert r.json()["quotes"] == []

    def test_ficha_pdf_rif_column(self, s, data):
        r = s.get(f"{BASE_URL}/api/projects/{data['pid']}/ficha-tecnica")
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"
        from pypdf import PdfReader
        txt = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
        assert "RIF / Sucursal" in txt
        assert "TESTSER" in txt


class TestBranchDetailsPrimary:
    """Primary quote with branch_details must still yield a multirif project (not multistore)."""

    def test_branch_details_primary(self, s):
        d = make_set("BD")
        try:
            C = d["_client"]("C", "TEST_MARCA_C")
            q1 = d["_quote"](C, "Aprobada", "c1", {"branch_details": [{"store_name": "TEST_Tienda Norte", "quantity": 2}]}, 0)
            q2 = d["_quote"](C, "Facturada", "c2", minutes=1)
            r = s.post(f"{BASE_URL}/api/multiprojects/create", json={"quote_ids": [q1, q2]})
            assert r.status_code == 200, r.text
            pj = db().projects.find_one({"project_id": r.json()["project_id"]}, {"_id": 0})
            d.setdefault("pids", []).append(pj["project_id"])
            print("project_type:", pj["project_type"], "stores:", [x.get("name") for x in pj.get("stores", [])])
            assert pj["project_type"] == "multirif", f"got {pj['project_type']} stores={[x.get('name') for x in pj.get('stores', [])]}"
        finally:
            cleanup(d, d.get("pids", []))
