"""Centro de Respaldos — 'Respaldo Total (1 clic)' con 19 entidades (iter 394).
Verifica: entities=19 (incl. 5 nuevas), export-zip con todas, import-preview-zip,
import-zip replace roundtrip con el MISMO ZIP recién exportado (conteos idénticos)
y que un TEST_ brand creado después del export es eliminado por replace.
"""
import io
import json
import os
import uuid
import zipfile

import pytest
import requests

if not os.environ.get("REACT_APP_BACKEND_URL"):
    with open("/app/frontend/.env") as _f:
        for _l in _f:
            if _l.startswith("REACT_APP_BACKEND_URL="):
                os.environ["REACT_APP_BACKEND_URL"] = _l.split("=", 1)[1].strip()

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
EMAIL = "qa.integradores@megasoft.com.ve"
PASSWORD = "QaIntegr2026*Ok"
NEW_MODULES = ["economic-groups", "brands", "integrator-companies", "integrator-certificates", "referentes"]

STATE = {}


@pytest.fixture(scope="module")
def h():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    b = r.json()
    tok = b.get("session_token") or b.get("token")
    if not tok:
        pytest.skip(f"no token: {b}")
    return {"Authorization": f"Bearer {tok}"}


def _counts(h):
    r = requests.get(f"{BASE_URL}/api/admin/backup-center/entities", headers=h, timeout=60)
    assert r.status_code == 200
    return {e["module"]: e["count"] for e in r.json()["entities"]}


# Entities list
def test_entities_19(h):
    r = requests.get(f"{BASE_URL}/api/admin/backup-center/entities", headers=h, timeout=60)
    assert r.status_code == 200
    ents = r.json()["entities"]
    assert len(ents) == 19
    mods = {e["module"]: e for e in ents}
    for m in NEW_MODULES:
        assert m in mods, m
        assert mods[m]["count"] > 0, m
    assert mods["brands"]["label"] == "Marcas o Nombre Fantasía"


def test_entities_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/backup-center/entities", timeout=30)
    assert r.status_code in (401, 403)


# Export ZIP + roundtrip replace
def test_export_zip_all_19(h):
    mods = list(_counts(h).keys())
    STATE["before"] = _counts(h)
    r = requests.post(f"{BASE_URL}/api/admin/backup-center/export-zip", headers=h,
                      json={"modules": mods}, timeout=300)
    assert r.status_code == 200, r.text[:300]
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(zf.namelist())
    assert "_manifest.json" in names
    assert len([n for n in names if n.endswith(".json") and n != "_manifest.json"]) == 19
    for m in NEW_MODULES:
        p = json.loads(zf.read(f"{m}.json"))
        assert p["module"] == m
        assert len(p["documents"]) == p["count"] == STATE["before"][m] > 0
    man = json.loads(zf.read("_manifest.json"))
    assert len(man["modules"]) == 19
    STATE["zip"] = r.content


def test_import_preview_zip(h):
    assert "zip" in STATE
    r = requests.post(f"{BASE_URL}/api/admin/backup-center/import-preview-zip", headers=h,
                      files={"file": ("respaldo_total.zip", STATE["zip"], "application/zip")}, timeout=300)
    assert r.status_code == 200, r.text[:300]
    b = r.json()
    assert b["total_entities"] == 19
    assert b["skipped_files"] == []
    recs = {e["module"]: e["records"] for e in b["entities"]}
    for m in NEW_MODULES:
        assert recs[m] == STATE["before"][m]


def test_create_test_brand_after_export(h):
    name = f"TEST_brand_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/api/marcas", headers=h, json={"name": name}, timeout=30)
    assert r.status_code == 200, r.text
    STATE["brand_id"] = r.json()["brand_id"]
    g = requests.get(f"{BASE_URL}/api/marcas/{STATE['brand_id']}", headers=h, timeout=30)
    assert g.status_code == 200


def test_import_zip_replace_roundtrip(h):
    assert "zip" in STATE
    r = requests.post(f"{BASE_URL}/api/admin/backup-center/import-zip", headers=h,
                      files={"file": ("respaldo_total.zip", STATE["zip"], "application/zip")},
                      data={"mode": "replace"}, timeout=600)
    assert r.status_code == 200, r.text[:300]
    b = r.json()
    assert b["errors"] == [], b["errors"]
    assert len(b["results"]) == 19
    res = {x["module"]: x for x in b["results"]}
    if "brand_id" in STATE:
        assert res["brands"]["deleted"] >= 1
    after = _counts(h)
    assert after == STATE["before"], {k: (STATE["before"].get(k), v) for k, v in after.items() if STATE["before"].get(k) != v}


def test_test_brand_removed_by_replace(h):
    bid = STATE.get("brand_id")
    assert bid
    g = requests.get(f"{BASE_URL}/api/marcas/{bid}", headers=h, timeout=30)
    assert g.status_code == 404
