"""Centro de Respaldos — Importación masiva en segundo plano (iter 395).
POST /api/admin/backup-center/import-zip-job -> job_id inmediato; GET .../{job_id} sondeo.
Roundtrip replace con el MISMO ZIP recién exportado (19 entidades); 409 concurrente; 400/404/403.
"""
import io
import os
import time
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
STATE = {}


def _login(email, pwd):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    if r.status_code != 200:
        return None
    b = r.json()
    tok = b.get("session_token") or b.get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else None


@pytest.fixture(scope="module")
def h():
    hh = _login(EMAIL, PASSWORD)
    if not hh:
        pytest.skip("login failed")
    return hh


def _counts(h):
    r = requests.get(f"{BASE_URL}/api/admin/backup-center/entities", headers=h, timeout=60)
    assert r.status_code == 200
    return {e["module"]: e["count"] for e in r.json()["entities"]}


# Export the 19-entity ZIP
def test_export_zip_19(h):
    before = _counts(h)
    assert len(before) == 19
    STATE["before"] = before
    r = requests.post(f"{BASE_URL}/api/admin/backup-center/export-zip", headers=h,
                      json={"modules": list(before.keys())}, timeout=300)
    assert r.status_code == 200, r.text[:300]
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert len([n for n in zf.namelist() if n.endswith(".json") and n != "_manifest.json"]) == 19
    STATE["zip"] = r.content
    with open("/tmp/respaldo_total_iter395.zip", "wb") as f:
        f.write(r.content)
    print(f"ZIP size: {len(r.content)/1e6:.2f} MB")


# Invalid inputs
def test_invalid_zip_400(h):
    t = time.time()
    r = requests.post(f"{BASE_URL}/api/admin/backup-center/import-zip-job", headers=h,
                      files={"file": ("bad.zip", b"not a zip", "application/zip")}, data={"mode": "replace"}, timeout=30)
    assert r.status_code == 400
    assert "ZIP" in r.json()["detail"]
    assert time.time() - t < 10


def test_non_zip_ext_400(h):
    r = requests.post(f"{BASE_URL}/api/admin/backup-center/import-zip-job", headers=h,
                      files={"file": ("x.txt", b"abc", "text/plain")}, timeout=30)
    assert r.status_code == 400


def test_unknown_job_404(h):
    r = requests.get(f"{BASE_URL}/api/admin/backup-center/import-zip-job/doesnotexist123", headers=h, timeout=30)
    assert r.status_code == 404


def test_no_auth_job(h):
    r = requests.get(f"{BASE_URL}/api/admin/backup-center/import-zip-job/x", timeout=30)
    assert r.status_code in (401, 403)
    r2 = requests.post(f"{BASE_URL}/api/admin/backup-center/import-zip-job",
                       files={"file": ("a.zip", b"x", "application/zip")}, timeout=30)
    assert r2.status_code in (401, 403)


# Job roundtrip + concurrency
def test_job_replace_roundtrip_and_409(h):
    assert "zip" in STATE
    t = time.time()
    r = requests.post(f"{BASE_URL}/api/admin/backup-center/import-zip-job", headers=h,
                      files={"file": ("respaldo_total.zip", STATE["zip"], "application/zip")},
                      data={"mode": "replace"}, timeout=60)
    elapsed = time.time() - t
    assert r.status_code == 200, r.text[:300]
    assert elapsed < 10, elapsed
    job_id = r.json()["job_id"]
    assert r.json()["status"] == "running"
    STATE["job_id"] = job_id
    print(f"POST elapsed {elapsed:.2f}s job={job_id}")

    # second POST while running -> 409
    r2 = requests.post(f"{BASE_URL}/api/admin/backup-center/import-zip-job", headers=h,
                       files={"file": ("respaldo_total.zip", STATE["zip"], "application/zip")},
                       data={"mode": "replace"}, timeout=60)
    STATE["second_status"] = r2.status_code
    assert r2.status_code == 409, r2.text[:200]

    deadline = time.time() + 600
    job = None
    progress_seen = set()
    while time.time() < deadline:
        g = requests.get(f"{BASE_URL}/api/admin/backup-center/import-zip-job/{job_id}", headers=h, timeout=30)
        if g.status_code == 401:
            # session could be replaced by user-permissions restore; re-login
            h.update(_login(EMAIL, PASSWORD) or {})
            continue
        assert g.status_code == 200, g.text[:200]
        job = g.json()
        progress_seen.add((job.get("done"), job.get("current_module")))
        if job["status"] != "running":
            break
        time.sleep(2.5)
    total_time = time.time() - t
    print(f"job finished in {total_time:.1f}s, progress samples: {len(progress_seen)}")
    assert job and job["status"] == "done", job
    res = job["result"]
    assert res["errors"] == [], res["errors"]
    assert len(res["results"]) == 19
    assert job["done"] == job["total"] == 19
    after = _counts(h)
    assert after == STATE["before"], {k: (STATE["before"].get(k), v) for k, v in after.items() if STATE["before"].get(k) != v}


# Non-admin 403 (kherrera, role user)
def test_non_admin_403():
    hh = _login("kherrera@megasoft.com.ve", "Kherrera2026*Qa")
    if not hh:
        pytest.skip("non-admin login unavailable")
    r = requests.get(f"{BASE_URL}/api/admin/backup-center/import-zip-job/x", headers=hh, timeout=30)
    assert r.status_code == 403
