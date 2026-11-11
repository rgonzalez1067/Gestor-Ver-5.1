# Iter380: removal of Datos de Imple (permission catalog + endpoint) and certificate counts for Integrators filter
import os
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    sess.headers.update({"Authorization": f"Bearer {r.json()['session_token']}"})
    return sess


# B: permission catalog has no datos_imple
def test_catalog_no_datos_imple(s):
    r = s.get(f"{BASE_URL}/api/admin/permission-catalog")
    assert r.status_code == 200
    assert "datos_imple" not in r.text
    assert "Datos de Imple" not in r.text


# B: imple-data endpoint removed
def test_imple_data_endpoint_removed(s):
    r = s.put(f"{BASE_URL}/api/clients/x/imple-data", json={})
    assert r.status_code in (404, 405), r.text[:200]


# C: certificate counts endpoint
def test_cert_counts(s):
    r = s.get(f"{BASE_URL}/api/integrators/certificates/counts")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    print("cert counts:", data)
