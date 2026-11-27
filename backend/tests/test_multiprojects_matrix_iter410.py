# Multiproyectos iter410: union of services/banks/matrix across all quotes, per-store matrix, per-quote summaries, PDF
import io
import os
import sys
import pytest
import requests
from pypdf import PdfReader

sys.path.insert(0, os.path.dirname(__file__))
from mp_fixture_iter409 import make_set, cleanup, db  # noqa: E402

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


def _login():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    d = r.json()
    tok = d.get("session_token") or d.get("token")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


def _pdf_text(content):
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)


@pytest.fixture(scope="module")
def ctx():
    s = _login()
    ids = make_set("M410")
    ca = ids["_client"]("A", "TEST_MarcaA")
    cb = ids["_client"]("B", "TEST_MarcaB")
    qa = ids["_quote"](ca, "Aprobada", 1, {"services": [{"item_type": "additional", "bank_name": "Banco X", "item_name": "Prod A", "quantity": 2}]}, minutes=0)
    qb = ids["_quote"](cb, "Aprobada", 2, {"services": [{"item_type": "additional", "bank_name": "Banco Y", "item_name": "Prod B", "quantity": 3}]}, minutes=5)
    out = {"s": s, "ids": ids, "qa": qa, "qb": qb, "pids": []}
    yield out
    cleanup(ids, out["pids"])


class TestMultiprojectMatrix:
    def test_preview_summaries(self, ctx):
        r = ctx["s"].post(f"{BASE_URL}/api/multiprojects/preview", json={"quote_ids": [ctx["qa"], ctx["qb"]]})
        assert r.status_code == 200, r.text
        sm = {x["quote_id"]: x for x in r.json()["summaries"]}
        assert len(sm) == 2
        assert sm[ctx["qa"]]["banks"] == ["Banco X"]
        assert sm[ctx["qb"]]["banks"] == ["Banco Y"]
        assert [x["item_name"] for x in sm[ctx["qa"]]["services"]] == ["Prod A"]
        assert [x["item_name"] for x in sm[ctx["qb"]]["services"]] == ["Prod B"]

    def test_create_and_project_union(self, ctx):
        r = ctx["s"].post(f"{BASE_URL}/api/multiprojects/create", json={"quote_ids": [ctx["qa"], ctx["qb"]], "implementation_instructions": "TEST_ins"})
        assert r.status_code == 200, r.text
        pid = r.json()["project_id"]
        ctx["pids"].append(pid)
        ctx["pid"] = pid
        p = db().projects.find_one({"project_id": pid}, {"_id": 0})
        ctx["project"] = p
        print("banks:", p.get("banks"), "matrix:", p.get("implementation_matrix"), "type:", p.get("project_type"))
        assert p["project_type"] == "multirif"
        banks = p.get("banks") or []
        bank_names = {b if isinstance(b, str) else (b.get("bank_name") or b.get("name")) for b in banks}
        assert {"Banco X", "Banco Y"} <= bank_names
        svc = {(x.get("bank_name"), x.get("item_name")) for x in p.get("services") or []}
        assert {("Banco X", "Prod A"), ("Banco Y", "Prod B")} <= svc
        assert set(p["implementation_matrix"]) == {"Banco X", "Banco Y"}

    def test_api_project_get(self, ctx):
        r = ctx["s"].get(f"{BASE_URL}/api/projects/{ctx['pid']}")
        assert r.status_code == 200
        d = r.json()
        assert len(d.get("quote_summaries") or []) == 2
        assert set(d.get("implementation_matrix") or {}) == {"Banco X", "Banco Y"}

    def test_store_matrices(self, ctx):
        p = ctx["project"]
        stores = p["stores"]
        assert len(stores) == 2
        sa = [s for s in stores if "TEST-COT-M410-1" in s["name"]][0]
        sb = [s for s in stores if "TEST-COT-M410-2" in s["name"]][0]
        assert list(sa["implementation_matrix"]) == ["Banco X"]
        assert list(sa["implementation_matrix"]["Banco X"]) == ["Prod A"]
        assert list(sb["implementation_matrix"]) == ["Banco Y"]
        assert list(sb["implementation_matrix"]["Banco Y"]) == ["Prod B"]
        assert len(p["quote_summaries"]) == 2

    def test_pdf_two_summaries(self, ctx):
        r = ctx["s"].get(f"{BASE_URL}/api/projects/{ctx['pid']}/ficha-tecnica")
        assert r.status_code == 200, r.text[:300]
        txt = _pdf_text(r.content)
        n = txt.count("Resumen Ejecutivo — Cotización") + txt.count("Resumen Ejecutivo - Cotización")
        print(txt[:3000])
        assert n == 2 or txt.count("Resumen Ejecutivo") >= 2
        assert "Banco X" in txt and "Banco Y" in txt
        assert "Prod A" in txt and "Prod B" in txt


class TestSingleProjectPdfRegression:
    def test_non_multiproject_pdf(self):
        s = _login()
        p = db().projects.find_one({"is_multiproject": {"$ne": True}, "project_type": "single", "quote_id": {"$exists": True}},
                                   {"_id": 0, "project_id": 1}, sort=[("created_at", -1)])
        if not p:
            pytest.skip("no single project")
        r = s.get(f"{BASE_URL}/api/projects/{p['project_id']}/ficha-tecnica")
        assert r.status_code == 200
        txt = _pdf_text(r.content)
        assert "Resumen Ejecutivo" in txt
        assert "Resumen Ejecutivo — Cotización" not in txt
        assert txt.count("Resumen Ejecutivo") == 1
