# Iter379: POST /api/marcas/report?format=pdf|xlsx (Reporte General de Marcas)
import io
import os
import subprocess

import fitz
import pytest
import requests
from openpyxl import load_workbook

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
FIX = os.path.join(os.path.dirname(__file__), "ui_fixture_iter377_brand_filters.py")
IDS = ["brd_test377_2", "brd_test377_3", "brd_test377_4"]
HEAD = ["Marca / Nombre Fantasía", "Grupo Económico", "RIF", "Razón Social", "Sucursales", "Segmento", "Ejecutivo Propietario"]


@pytest.fixture(scope="module", autouse=True)
def data():
    subprocess.run(["python", FIX, "setup"], check=True)
    yield
    subprocess.run(["python", FIX, "cleanup"], check=True)


@pytest.fixture(scope="module")
def admin():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if r.status_code != 200 or "session_token" not in r.json():
        pytest.skip(f"login failed: {r.text[:200]}")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['session_token']}"})
    return s


def test_pdf(admin):
    r = admin.post(f"{BASE_URL}/api/marcas/report?format=pdf", json={"brand_ids": IDS, "filters_label": "Segmento: Mixto"})
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"].startswith("application/pdf")
    assert "Reporte_Marcas_" in r.headers.get("content-disposition", "")
    doc = fitz.open(stream=r.content, filetype="pdf")
    text = " ".join(p.get_text() for p in doc)
    assert "Reporte General de Marcas" in text
    for n in ("TEST_377 Beta", "TEST_377 Gamma", "TEST_377 Delta"):
        assert n in text
    assert "TEST_377 Alfa" not in text
    assert "J-037700002-1" in text  # format_rif zero-pads to 9 digits
    assert "Sin RIF asociados" in text
    assert "Segmento: Mixto" in text
    assert "3 marcas" in text and "3 RIF" in text


def test_xlsx(admin):
    r = admin.post(f"{BASE_URL}/api/marcas/report?format=xlsx", json={"brand_ids": IDS})
    assert r.status_code == 200, r.text[:300]
    assert "spreadsheetml" in r.headers["content-type"]
    ws = load_workbook(io.BytesIO(r.content)).active
    rows = list(ws.iter_rows(values_only=True))
    assert list(rows[0]) == HEAD
    body = rows[1:]
    assert {x[0] for x in body} == {"TEST_377 Beta", "TEST_377 Gamma", "TEST_377 Delta"}
    beta = [x for x in body if x[0] == "TEST_377 Beta"]
    assert len(beta) == 2 and all(x[1] == "TEST_377 Grupo A" for x in beta)
    assert {x[5] for x in beta} == {"Corporativo", None} or {x[5] for x in beta} == {"Corporativo", ""}
    assert any(x[6] == "TEST_377 Ejecutivo Dos" for x in beta)
    delta = [x for x in body if x[0] == "TEST_377 Delta"]
    assert len(delta) == 1 and delta[0][3] == "Sin RIF asociados"
    assert all(isinstance(x[4], int) for x in body)


def test_empty_400(admin):
    r = admin.post(f"{BASE_URL}/api/marcas/report?format=pdf", json={"brand_ids": []})
    assert r.status_code == 400
    assert "marcas" in r.json().get("detail", "").lower()


def test_unauth():
    r = requests.post(f"{BASE_URL}/api/marcas/report?format=pdf", json={"brand_ids": IDS})
    assert r.status_code == 401


def test_all_brands_pdf(admin):
    ids = [b["brand_id"] for b in admin.get(f"{BASE_URL}/api/marcas").json()]
    r = admin.post(f"{BASE_URL}/api/marcas/report?format=pdf", json={"brand_ids": ids}, timeout=60)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    print("all brands", len(ids), "pdf bytes", len(r.content), "secs", r.elapsed.total_seconds())
