# Iter354: Report params (include_processors / include_pre_production) for
# 'Productos por Banco' and 'Bancos por Producto' PDF reports. Read-only tests.
import os
import re
import io
import pytest
import requests
import fitz

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
PROCESSORS = ["Consorcio CrediCard", "Platco", "Tranred"]
PHASE_TAGS = ["[DESA]", "[SQA]", "[Imple]", "[Primer Prod]"]
ENDPOINTS = {
    "pbb": "/api/banks/report/products-by-bank/pdf",
    "bbp": "/api/services/report/banks-by-product/pdf",
}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    tok = r.json().get("session_token") or r.json().get("token")
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


_cache = {}


def pdf_text(client, key, procs, pre):
    ck = (key, procs, pre)
    if ck in _cache:
        return _cache[ck]
    params = {}
    if procs is not None:
        params["include_processors"] = str(procs).lower()
    if pre is not None:
        params["include_pre_production"] = str(pre).lower()
    r = client.get(f"{BASE_URL}{ENDPOINTS[key]}", params=params, timeout=120)
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    doc = fitz.open(stream=io.BytesIO(r.content), filetype="pdf")
    txt = "\n".join(p.get_text() for p in doc)
    txt = re.sub(r"[ \t]+", " ", txt)
    _cache[ck] = txt
    return txt


def flat(t):
    return re.sub(r"\s+", " ", t)


# Processor scope
@pytest.mark.parametrize("key", ["pbb", "bbp"])
def test_default_excludes_processors_and_preprod(client, key):
    t = flat(pdf_text(client, key, None, None))
    for p in PROCESSORS:
        assert p not in t, f"{p} found in default {key}"
    for tag in PHASE_TAGS:
        assert tag not in t
    assert "Filtros:" in t
    assert "Solo Bancos/Entes (sin Procesadores)" in t
    assert "Solo productos en Producción" in t


# NOTE: bbp excluded — the 3 Procesador banks have products=[] in DB, so they can never
# appear as associated banks in 'Bancos por Producto' (data limitation, not a bug).
@pytest.mark.parametrize("key", ["pbb"])
def test_include_processors_true(client, key):
    t = flat(pdf_text(client, key, True, False))
    for p in PROCESSORS:
        assert p in t, f"{p} missing in {key} with include_processors=true"
    assert "Bancos/Entes y Procesadores" in t
    for tag in PHASE_TAGS:
        assert tag not in t


@pytest.mark.parametrize("key", ["pbb", "bbp"])
def test_include_preprod_true(client, key):
    t = flat(pdf_text(client, key, False, True))
    assert "[Imple]" in t
    assert "[Producción]" not in t
    assert "Incluye fases no productivas" in t
    for p in PROCESSORS:
        assert p not in t


@pytest.mark.parametrize("key", ["pbb", "bbp"])
def test_imple_count(client, key):
    t = flat(pdf_text(client, key, True, True))
    n = t.count("[Imple]")
    print(f"{key} [Imple] count with all=true: {n}")
    assert n >= 1
    assert "[Producción]" not in t


def test_imple_count_matches_db(client):
    r = client.get(f"{BASE_URL}/api/banks", timeout=60)
    assert r.status_code == 200
    data = r.json()
    banks = data if isinstance(data, list) else data.get("banks", data.get("items", []))
    def phase(p):
        return p.get("operational_status") or ("Imple" if p.get("pre_production") else "Producción")
    imple = sum(1 for b in banks for p in (b.get("products") or []) if phase(p) == "Imple")
    nonprod = sum(1 for b in banks for p in (b.get("products") or []) if phase(p) != "Producción")
    print(f"DB: Imple={imple}, nonprod={nonprod}")
    t = flat(pdf_text(client, "pbb", True, True))
    assert t.count("[Imple]") == imple


def test_unauthenticated_rejected():
    r = requests.get(f"{BASE_URL}{ENDPOINTS['pbb']}", timeout=60)
    assert r.status_code in (401, 403)
