# Iter377: GET /api/marcas returns segments[] and ejecutivos[] per brand (brand + its RIFs)
import os
import subprocess

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
FIX = os.path.join(os.path.dirname(__file__), "ui_fixture_iter377_brand_filters.py")


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


@pytest.fixture(scope="module")
def rows(admin):
    r = admin.get(f"{BASE_URL}/api/marcas", params={"search": "TEST_377"})
    assert r.status_code == 200
    return {b["brand_id"]: b for b in r.json()}


def test_all_rows_have_fields(admin):
    r = admin.get(f"{BASE_URL}/api/marcas")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 500
    for b in data:
        assert isinstance(b["segments"], list) and isinstance(b["ejecutivos"], list)
        for e in b["ejecutivos"]:
            assert set(e) == {"id", "name"} and e["id"]


def test_brand_only_values(rows):
    b = rows["brd_test377_1"]
    assert b["segments"] == ["Pymes"]
    assert b["ejecutivos"] == [{"id": "usr_test377_ej1", "name": "TEST_377 Ejecutivo Uno"}]


def test_rif_values_and_null_segment_excluded(rows):
    b = rows["brd_test377_2"]
    assert b["segments"] == ["Corporativo"]
    ids = sorted(e["id"] for e in b["ejecutivos"])
    assert ids == ["TEST_377 SoloNombre", "usr_test377_ej2"]
    assert b["rif_count"] == 2


def test_union_brand_and_rif(rows):
    b = rows["brd_test377_3"]
    assert b["segments"] == ["Mixto", "Pymes"]
    assert b["ejecutivos"] == [{"id": "usr_test377_ej1", "name": "TEST_377 Ejecutivo Uno"}]


def test_empty_brand(rows):
    b = rows["brd_test377_4"]
    assert b["segments"] == [] and b["ejecutivos"] == [] and b["group_id"] is None


def test_group_endpoint_has_fields(admin):
    r = admin.get(f"{BASE_URL}/api/grupos-economicos/grp_test377_a/marcas")
    assert r.status_code == 200
    ids = {b["brand_id"]: b for b in r.json()}
    assert set(ids) == {"brd_test377_1", "brd_test377_2"}
    assert ids["brd_test377_2"]["segments"] == ["Corporativo"]
