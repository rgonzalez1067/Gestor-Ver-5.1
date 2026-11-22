# Single successful-login validation for rgonzalez (customer case). NO negative tests.
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


def test_rgonzalez_login_ok():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}, timeout=30)
    print(r.status_code, {k: v for k, v in r.json().items() if k != "session_token"})
    assert r.status_code == 200
    d = r.json()
    assert d.get("status") not in ("PASSWORD_EXPIRED", "2FA_CHALLENGE")
    assert isinstance(d.get("session_token"), str) and d["session_token"]
    assert d["user"]["role"] == "admin"
    assert d["user"]["email"] == "rgonzalez@megasoft.com.ve"
