# Security Policy module tests (iter359): tablero, complejidad, historial, bloqueo, vencimiento, 2FA, reset-password
import os
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
DEFAULTS = {"password_max_age_days": 90, "expiry_warning_days": 7, "password_history_count": 5,
            "max_failed_attempts": 5, "lockout_minutes": 15, "two_factor_enabled": False,
            "min_password_length": 12, "otp_ttl_minutes": 10}
PWD_A = "TestAlpha#2026x"
PWD_B = "TestBravo#2026x"
PWD_C = "TestCharl#2026x"

mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def login(email, password):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)


@pytest.fixture(scope="module")
def admin_h():
    r = login(**ADMIN)
    assert r.status_code == 200, r.text
    assert r.json().get("session_token"), r.text
    return {"Authorization": f"Bearer {r.json()['session_token']}"}


@pytest.fixture(scope="module")
def created_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def restore(created_ids):
    yield
    r = login(**ADMIN)
    h = {"Authorization": f"Bearer {r.json()['session_token']}"}
    requests.put(f"{API}/admin/security-policy", json=DEFAULTS, headers=h, timeout=30)
    for uid in created_ids:
        mdb.users.delete_one({"user_id": uid})
        mdb.user_password_history.delete_many({"user_id": uid})
        mdb.user_sessions.delete_many({"user_id": uid})
        mdb.login_2fa_challenges.delete_many({"user_id": uid})
        mdb.password_change_tokens.delete_many({"user_id": uid})
        mdb.password_reset_tokens.delete_many({"user_id": uid})


def set_policy(h, **kw):
    r = requests.put(f"{API}/admin/security-policy", json={**DEFAULTS, **kw}, headers=h, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def mk_user(h, created_ids, pwd=PWD_A):
    email = f"test_sec_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/admin/users/create", headers=h, timeout=30, json={
        "first_name": "TEST_Sec", "last_name": "User", "email": email, "password": pwd, "sede": "PYME"})
    assert r.status_code in (200, 201), r.text
    uid = mdb.users.find_one({"email": email})["user_id"]
    created_ids.append(uid)
    return email, uid


# ---------- Tablero ----------
class TestPolicyBoard:
    def test_get_defaults_shape(self, admin_h):
        r = requests.get(f"{API}/admin/security-policy", headers=admin_h)
        assert r.status_code == 200
        assert set(DEFAULTS).issubset(r.json().keys())

    def test_save_and_persist(self, admin_h):
        set_policy(admin_h, min_password_length=14, max_failed_attempts=3, lockout_minutes=15, password_history_count=3)
        g = requests.get(f"{API}/admin/security-policy", headers=admin_h).json()
        assert g["min_password_length"] == 14 and g["max_failed_attempts"] == 3
        assert g["password_history_count"] == 3 and g["lockout_minutes"] == 15
        pub = requests.get(f"{API}/auth/password-policy").json()
        assert pub["min_password_length"] == 14
        set_policy(admin_h)

    def test_warning_ge_age_400(self, admin_h):
        r = requests.put(f"{API}/admin/security-policy", json={"expiry_warning_days": 90, "password_max_age_days": 90}, headers=admin_h)
        assert r.status_code == 400

    def test_min_length_lt_12_400(self, admin_h):
        r = requests.put(f"{API}/admin/security-policy", json={"min_password_length": 11}, headers=admin_h)
        assert r.status_code == 400

    def test_non_admin_403(self, admin_h, created_ids):
        email, _ = mk_user(admin_h, created_ids)
        tok = login(email, PWD_A).json()["session_token"]
        h = {"Authorization": f"Bearer {tok}"}
        assert requests.get(f"{API}/admin/security-policy", headers=h).status_code == 403
        assert requests.put(f"{API}/admin/security-policy", json={"lockout_minutes": 1}, headers=h).status_code == 403


# ---------- Complejidad + historial ----------
class TestComplexityHistory:
    def test_complexity_and_history(self, admin_h, created_ids):
        set_policy(admin_h, password_history_count=3)
        email, uid = mk_user(admin_h, created_ids)
        h = {"Authorization": f"Bearer {login(email, PWD_A).json()['session_token']}"}
        cp = lambda cur, new: requests.post(f"{API}/auth/change-password", headers=h, json={"current_password": cur, "new_password": new})
        r = cp(PWD_A, "Abcdefg#123")  # 11 chars
        assert r.status_code == 400 and "12 caracteres" in r.json()["detail"]
        r = cp(PWD_A, "Abcdefgh1234")  # 12 sin especial
        assert r.status_code == 400 and "especial" in r.json()["detail"]
        assert cp(PWD_A, PWD_B).status_code == 200
        assert cp(PWD_B, PWD_C).status_code == 200
        r = cp(PWD_C, PWD_A)
        assert r.status_code == 400
        assert r.json()["detail"] == "Contraseña Inválida: No puede utilizar ninguna de sus últimas 3 contraseñas anteriores."
        assert mdb.user_password_history.count_documents({"user_id": uid}) == 2


# ---------- Bloqueo ----------
class TestLockout:
    def test_lockout_flow(self, admin_h, created_ids):
        set_policy(admin_h, max_failed_attempts=3, lockout_minutes=15)
        email, uid = mk_user(admin_h, created_ids)
        assert login(email, "Wrong#Pass12345").status_code == 401
        assert login(email, "Wrong#Pass12345").status_code == 401
        r = login(email, "Wrong#Pass12345")
        assert r.status_code == 423 and "Cuenta bloqueada temporalmente" in r.json()["detail"] and "15 minutos" in r.json()["detail"]
        r = login(email, PWD_A)
        assert r.status_code == 423
        # simular 16 min
        mdb.users.update_one({"user_id": uid}, {"$set": {"lockout_timestamp": (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()}})
        r = login(email, PWD_A)
        assert r.status_code == 200 and r.json().get("session_token")
        u = mdb.users.find_one({"user_id": uid})
        assert u["account_status"] == "ACTIVE" and u["failed_login_attempts"] == 0
        # admin unlock
        for _ in range(3):
            login(email, "Wrong#Pass12345")
        assert login(email, PWD_A).status_code == 423
        r = requests.post(f"{API}/admin/users/{uid}/unlock", headers=admin_h)
        assert r.status_code == 200
        assert login(email, PWD_A).status_code == 200

    def test_unlock_404(self, admin_h):
        assert requests.post(f"{API}/admin/users/nonexistent_x/unlock", headers=admin_h).status_code == 404


# ---------- Vencimiento ----------
class TestExpiry:
    def test_expired_flow(self, admin_h, created_ids):
        set_policy(admin_h)
        email, uid = mk_user(admin_h, created_ids)
        mdb.users.update_one({"user_id": uid}, {"$set": {"password_changed_at": (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()}})
        r = login(email, PWD_A)
        assert r.status_code == 200 and r.json()["status"] == "PASSWORD_EXPIRED" and "session_token" not in r.json()
        tok = r.json()["change_token"]
        bad = requests.post(f"{API}/auth/expired-password/change", json={"change_token": tok, "new_password": PWD_A})
        assert bad.status_code == 400  # reuse current
        weak = requests.post(f"{API}/auth/expired-password/change", json={"change_token": tok, "new_password": "short1A!"})
        assert weak.status_code == 400
        ok = requests.post(f"{API}/auth/expired-password/change", json={"change_token": tok, "new_password": PWD_B})
        assert ok.status_code == 200, ok.text
        r = login(email, PWD_B)
        assert r.status_code == 200 and r.json().get("session_token")
        # token single-use
        again = requests.post(f"{API}/auth/expired-password/change", json={"change_token": tok, "new_password": PWD_C})
        assert again.status_code == 400

    def test_warning_window(self, admin_h, created_ids):
        email, uid = mk_user(admin_h, created_ids)
        mdb.users.update_one({"user_id": uid}, {"$set": {"password_changed_at": (datetime.now(timezone.utc) - timedelta(days=85)).isoformat()}})
        r = login(email, PWD_A)
        assert r.status_code == 200 and r.json()["password_expires_in_days"] == 5
        mdb.users.update_one({"user_id": uid}, {"$set": {"password_changed_at": datetime.now(timezone.utc).isoformat()}})
        assert login(email, PWD_A).json()["password_expires_in_days"] is None


# ---------- 2FA ----------
class TestTwoFactor:
    def test_2fa_flow(self, admin_h, created_ids):
        email, uid = mk_user(admin_h, created_ids)
        set_policy(admin_h, two_factor_enabled=True)
        try:
            r = login(email, PWD_A)
            assert r.status_code == 200 and r.json()["status"] == "2FA_CHALLENGE", r.text
            d = r.json()
            assert d["challenge_id"] and "*" in d["email_masked"] and d["ttl_minutes"] == 10
            code = "123456"
            mdb.login_2fa_challenges.update_one({"challenge_id": d["challenge_id"]}, {"$set": {"code_hash": hashlib.sha256(code.encode()).hexdigest()}})
            w = requests.post(f"{API}/auth/2fa/verify", json={"challenge_id": d["challenge_id"], "code": "000000"})
            assert w.status_code == 400 and w.json()["detail"] == "Código incorrecto."
            rs = requests.post(f"{API}/auth/2fa/resend", json={"challenge_id": d["challenge_id"]})
            assert rs.status_code == 200
            mdb.login_2fa_challenges.update_one({"challenge_id": d["challenge_id"]}, {"$set": {"code_hash": hashlib.sha256(code.encode()).hexdigest()}})
            ok = requests.post(f"{API}/auth/2fa/verify", json={"challenge_id": d["challenge_id"], "code": code})
            assert ok.status_code == 200 and ok.json().get("session_token")
            reuse = requests.post(f"{API}/auth/2fa/verify", json={"challenge_id": d["challenge_id"], "code": code})
            assert reuse.status_code == 400
            # wrong password with 2FA still 401
            assert login(email, "Wrong#Pass12345").status_code == 401
        finally:
            set_policy(admin_h, two_factor_enabled=False)
        r = login(email, PWD_A)
        assert r.status_code == 200 and r.json().get("session_token")

    def test_2fa_bruteforce_limit(self, admin_h, created_ids):
        email, uid = mk_user(admin_h, created_ids)
        set_policy(admin_h, two_factor_enabled=True)
        try:
            cid = login(email, PWD_A).json()["challenge_id"]
            for _ in range(5):
                requests.post(f"{API}/auth/2fa/verify", json={"challenge_id": cid, "code": "999999"})
            r = requests.post(f"{API}/auth/2fa/verify", json={"challenge_id": cid, "code": "999999"})
            assert r.status_code == 400 and "Demasiados" in r.json()["detail"]
        finally:
            set_policy(admin_h, two_factor_enabled=False)


# ---------- Reset-password (regresión) ----------
class TestResetPassword:
    def test_reset_applies_policy(self, admin_h, created_ids):
        set_policy(admin_h, password_history_count=3)
        email, uid = mk_user(admin_h, created_ids)
        tok = secrets.token_urlsafe(24)
        mdb.password_reset_tokens.insert_one({"token": tok, "user_id": uid, "used": False,
                                              "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
        r = requests.post(f"{API}/auth/reset-password", json={"token": tok, "new_password": "Abcdefgh1234"})
        assert r.status_code == 400 and "especial" in r.json()["detail"]
        r = requests.post(f"{API}/auth/reset-password", json={"token": tok, "new_password": PWD_A})
        assert r.status_code == 400 and "últimas 3" in r.json()["detail"]
        r = requests.post(f"{API}/auth/reset-password", json={"token": tok, "new_password": PWD_B})
        assert r.status_code == 200, r.text
        assert login(email, PWD_B).status_code == 200
