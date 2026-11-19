# Bitácora: evidencia visual (upload/get) + normalización "Al día" (sla_reset_at) — iter 384
import io
import os
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
ADMIN = ("rgonzalez@megasoft.com.ve", "MegaSoft2026*")
JROJAS = ("jrojas@megasoft.com.ve", "Test1234!")
KHERRERA = ("kherrera@megasoft.com.ve", "Kherrera2026*Qa")
REUSE_PID = "prj_10e879128c18"  # ya puesto Al día por E1; reutilizado para set_al_dia OK


def _login(email, pwd):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200 or "session_token" not in r.json():
        pytest.skip(f"login failed {email}: {r.text[:200]}")
    d = r.json()
    return {"Authorization": f"Bearer {d['session_token']}"}, d["user"]


def _png(w=40, h=30):
    b = io.BytesIO()
    Image.new("RGB", (w, h), (200, 30, 30)).save(b, "PNG")
    return b.getvalue()


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def jrojas():
    return _login(*JROJAS)


@pytest.fixture(scope="module")
def kherrera():
    return _login(*KHERRERA)


@pytest.fixture(scope="module")
def projects(admin):
    r = requests.get(f"{BASE_URL}/api/projects", headers=admin[0])
    assert r.status_code == 200
    return r.json()


def _upload(h, pid, name="TEST_ev.png", data=None, ct="image/png"):
    return requests.post(f"{BASE_URL}/api/projects/{pid}/bitacora/evidence", headers=h,
                         files={"file": (name, data if data is not None else _png(), ct)})


class TestEvidenceUpload:
    def test_upload_png_and_get(self, admin):
        r = _upload(admin[0], REUSE_PID)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["evidence_id"].startswith("evd_") and d["size"] > 0
        g = requests.get(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora/evidence/{d['evidence_id']}", headers=admin[0])
        assert g.status_code == 200
        assert g.headers["content-type"].startswith("image/")
        assert len(g.content) > 0

    def test_get_without_auth_401(self, admin):
        r = _upload(admin[0], REUSE_PID)
        eid = r.json()["evidence_id"]
        g = requests.get(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora/evidence/{eid}")
        assert g.status_code == 401

    def test_get_unknown_404(self, admin):
        g = requests.get(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora/evidence/evd_nope", headers=admin[0])
        assert g.status_code == 404

    def test_reject_exe(self, admin):
        r = _upload(admin[0], REUSE_PID, "TEST_virus.exe", b"MZ\x90\x00" * 100, "application/octet-stream")
        assert r.status_code == 400
        assert "JPG" in r.json()["detail"]

    def test_reject_fake_png(self, admin):
        r = _upload(admin[0], REUSE_PID, "TEST_fake.png", b"not an image" * 10, "image/png")
        assert r.status_code == 400

    def test_reject_over_5mb(self, admin):
        r = _upload(admin[0], REUSE_PID, "TEST_big.png", b"\x89PNG" + b"0" * (5 * 1024 * 1024 + 10), "image/png")
        assert r.status_code == 400
        assert "5 MB" in r.json()["detail"]

    def test_upload_unknown_project_404(self, admin):
        r = _upload(admin[0], "prj_doesnotexist")
        assert r.status_code == 404


class TestBitacoraAlDia:
    def test_al_dia_without_evidence_400(self, admin):
        r = requests.post(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora", headers=admin[0],
                          json={"text": "TEST_no_ev", "execution_date": "2026-01-15", "evidence_ids": [], "set_al_dia": True})
        assert r.status_code == 400

    def test_more_than_5_evidence_400(self, admin):
        ids = [_upload(admin[0], REUSE_PID).json()["evidence_id"] for _ in range(6)]
        r = requests.post(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora", headers=admin[0],
                          json={"text": "TEST_6", "execution_date": "2026-01-15", "evidence_ids": ids})
        assert r.status_code == 400
        assert "5" in r.json()["detail"]

    def test_al_dia_by_non_assigned_403(self, kherrera, admin, projects):
        p = next(p for p in projects if p.get("assigned_to_user_id") != kherrera[1]["user_id"])
        eid = _upload(admin[0], p["project_id"]).json()["evidence_id"]
        r = requests.post(f"{BASE_URL}/api/projects/{p['project_id']}/bitacora", headers=kherrera[0],
                          json={"text": "TEST_403", "execution_date": "2026-01-15", "evidence_ids": [eid], "set_al_dia": True})
        assert r.status_code == 403, r.text

    def test_al_dia_ok_admin_and_reset(self, admin):
        eid = _upload(admin[0], REUSE_PID).json()["evidence_id"]
        r = requests.post(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora", headers=admin[0],
                          json={"text": "TEST_al_dia", "execution_date": "2026-01-15", "evidence_ids": [eid], "set_al_dia": True})
        assert r.status_code == 200, r.text
        e = r.json()
        assert e["set_al_dia"] is True and e["evidence"][0]["evidence_id"] == eid
        # Reusar evidencia ya vinculada -> 400
        r2 = requests.post(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora", headers=admin[0],
                           json={"text": "TEST_reuse", "execution_date": "2026-01-15", "evidence_ids": [eid]})
        assert r2.status_code == 400
        p = requests.get(f"{BASE_URL}/api/projects/{REUSE_PID}", headers=admin[0]).json()
        assert p.get("sla_reset_at")
        lst = requests.get(f"{BASE_URL}/api/projects", headers=admin[0]).json()
        row = next(x for x in lst if x["project_id"] == REUSE_PID)
        assert row["business_days_in_state"] == 0

    def test_al_dia_by_assigned_implementer_ok(self, jrojas, admin, projects):
        mine = [p for p in projects if p.get("assigned_to_user_id") == jrojas[1]["user_id"]]
        if not mine:
            pytest.skip("jrojas sin proyectos asignados")
        pid = mine[0]["project_id"]
        eid = _upload(jrojas[0], pid).json()["evidence_id"]
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/bitacora", headers=jrojas[0],
                          json={"text": "TEST_impl_al_dia", "execution_date": "2026-01-15", "evidence_ids": [eid], "set_al_dia": True})
        assert r.status_code == 200, r.text

    def test_plain_note_regression(self, admin):
        r = requests.post(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora", headers=admin[0],
                          json={"text": "TEST_plain", "execution_date": "2026-01-15"})
        assert r.status_code == 200
        assert r.json()["set_al_dia"] is False and r.json()["evidence"] == []
        b = requests.get(f"{BASE_URL}/api/projects/{REUSE_PID}/bitacora", headers=admin[0]).json()
        assert any(x.get("entry_id") == r.json()["entry_id"] for x in b)
