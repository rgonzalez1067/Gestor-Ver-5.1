# Quotes-bundle migration: preview-keys / import-batch / import-finalize + legacy endpoints
import json
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    for line in open('/app/frontend/.env'):
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip().strip('"').rstrip('/')
API = f"{BASE_URL}/api/admin/quotes-bundle-migration"


def _login(email, pwd):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    if r.status_code != 200:
        return None
    d = r.json()
    return d.get("session_token") or d.get("token") or d.get("access_token")


@pytest.fixture(scope="module")
def admin_h():
    t = _login("rgonzalez@megasoft.com.ve", "Mega2026*") or _login("rgonzalez@megasoft.com.ve", "admin123")
    if not t:
        pytest.skip("admin login failed")
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def user_h():
    t = _login("kherrera@megasoft.com.ve", "Test1234!")
    if not t:
        pytest.skip("non-admin login failed")
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def real_bundle():
    return json.load(open('/tmp/bundle.json'))


# Preview-keys: summary counts for real export (all update)
def test_preview_keys_real(admin_h, real_bundle):
    keys = {c: [d["quote_id" if c == "quotes" else "history_id" if c == "quote_history" else "project_id"] for d in docs]
            for c, docs in real_bundle["collections"].items()}
    r = requests.post(f"{API}/preview-keys", json={"keys": keys, "invalid": {}}, headers=admin_h, timeout=60)
    assert r.status_code == 200, r.text
    s = {x["collection"]: x for x in r.json()["summary"]}
    assert s["quotes"]["to_update"] == 5 and s["quotes"]["to_create"] == 0
    assert s["quote_history"]["to_update"] == 6
    assert s["projects"]["to_update"] == 382 and s["projects"]["to_create"] == 0


# Preview-keys: fake keys counted as create, invalid counted
def test_preview_keys_fake_and_invalid(admin_h):
    r = requests.post(f"{API}/preview-keys", json={"keys": {"projects": ["zzfake_TEST_1", "zzfake_TEST_2"]},
                                                   "invalid": {"projects": 3}}, headers=admin_h, timeout=30)
    assert r.status_code == 200
    p = [x for x in r.json()["summary"] if x["collection"] == "projects"][0]
    assert p["to_create"] == 2 and p["invalid"] == 3 and p["total_in_file"] == 5


# Auth: endpoints require admin
@pytest.mark.parametrize("ep,body", [
    ("preview-keys", {"keys": {}}),
    ("import-batch", {"collection": "projects", "documents": []}),
    ("import-finalize", {"results": []}),
])
def test_requires_admin(ep, body, user_h):
    r = requests.post(f"{API}/{ep}", json=body, timeout=30)
    assert r.status_code in (401, 403)
    r = requests.post(f"{API}/{ep}", json=body, headers=user_h, timeout=30)
    assert r.status_code in (401, 403), r.text


# import-batch rejects collections outside whitelist
@pytest.mark.parametrize("col", ["users", "bitacora", "clients"])
def test_import_batch_rejects_collection(admin_h, col):
    r = requests.post(f"{API}/import-batch", json={"collection": col, "documents": [{"x": 1}]}, headers=admin_h, timeout=30)
    assert r.status_code == 400
    assert "no permitida" in r.json()["detail"]


# import-batch: missing key → skipped, no insert
def test_import_batch_missing_key(admin_h):
    r = requests.post(f"{API}/import-batch", json={"collection": "projects", "documents": [{"name": "TEST_nokey"}]},
                      headers=admin_h, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["skipped"] == 1 and d["inserted"] == 0


# import-batch: real docs → idempotent update
def test_import_batch_real_update(admin_h, real_bundle):
    docs = real_bundle["collections"]["quotes"]
    r = requests.post(f"{API}/import-batch", json={"collection": "quotes", "documents": docs}, headers=admin_h, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["updated"] == 5 and d["inserted"] == 0 and d["skipped"] == 0


# Legacy endpoints still work (import-preview with real file)
def test_legacy_import_preview(admin_h):
    with open('/tmp/bundle.json', 'rb') as f:
        r = requests.post(f"{API}/import-preview", files={"file": ("bundle.json", f, "application/json")},
                          headers=admin_h, timeout=120)
    assert r.status_code == 200, r.text[:300]
    s = {x["collection"]: x for x in r.json()["summary"]}
    assert s["projects"]["to_update"] == 382


# Legacy import-data with small bundle (quotes only, idempotent)
def test_legacy_import_data_small(admin_h, real_bundle):
    small = {"module": "quotes-bundle", "exported_at": "TEST", "collections": {"quotes": real_bundle["collections"]["quotes"]}}
    r = requests.post(f"{API}/import-data", files={"file": ("s.json", json.dumps(small), "application/json")},
                      headers=admin_h, timeout=120)
    assert r.status_code == 200, r.text[:300]
    assert r.json()["totals"]["inserted"] == 0


# Legacy import-preview rejects wrong module
def test_legacy_wrong_module(admin_h):
    r = requests.post(f"{API}/import-preview", files={"file": ("x.json", json.dumps({"module": "clients"}), "application/json")},
                      headers=admin_h, timeout=30)
    assert r.status_code == 400
