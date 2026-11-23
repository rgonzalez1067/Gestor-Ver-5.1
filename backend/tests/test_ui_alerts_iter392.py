# UI Alerts (Avisos en Pantalla) - settings + per-user evaluation (iter392)
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    with open('/app/frontend/.env') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                BASE_URL = line.split('=', 1)[1].strip().rstrip('/')

ADMIN = ("qa.integradores@megasoft.com.ve", "QaIntegr2026*Ok")
NONADMIN = ("qa.editor@megasoft.com.ve", "QaIntegr2026*Ok")
ME_ID = "user_qaintegr01"
ME_DEPT = "Ventas Pyme"


def _login(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"login failed {email}: {r.status_code}")
    tok = r.json().get("session_token") or r.json().get("token")
    if not tok:
        pytest.skip(f"no token {email}: {r.json()}")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def admin():
    s = _login(*ADMIN)
    yield s
    r = s.put(f"{BASE_URL}/api/settings/ui-alerts", json={})
    assert r.status_code == 200


@pytest.fixture(scope="module")
def nonadmin():
    return _login(*NONADMIN)


def _put(s, cfg):
    r = s.put(f"{BASE_URL}/api/settings/ui-alerts", json=cfg)
    assert r.status_code == 200, r.text
    return r


def _me(s):
    r = s.get(f"{BASE_URL}/api/notifications/ui-alerts/me")
    assert r.status_code == 200
    return r.json()


class TestUiAlerts:
    def test_get_structure(self, admin):
        _put(admin, {})
        r = admin.get(f"{BASE_URL}/api/settings/ui-alerts")
        assert r.status_code == 200
        d = r.json()
        assert set(d["config"].keys()) == {"push", "unread_banner"}
        assert d["config"]["push"] == {"enabled": True, "disabled_departments": [], "disabled_users": []}
        assert ME_DEPT in d["departments"]
        assert any(u["user_id"] == ME_ID for u in d["users"])
        assert all("_id" not in u for u in d["users"])

    def test_me_all_on(self, admin):
        _put(admin, {})
        assert _me(admin) == {"push": True, "unread_banner": True}

    def test_global_off(self, admin):
        _put(admin, {"unread_banner": {"enabled": False}})
        assert _me(admin) == {"push": True, "unread_banner": False}

    def test_dept_off(self, admin):
        _put(admin, {"push": {"enabled": True, "disabled_departments": [ME_DEPT]}})
        assert _me(admin) == {"push": False, "unread_banner": True}

    def test_other_dept_off_no_effect(self, admin):
        _put(admin, {"push": {"disabled_departments": ["Operaciones"]}})
        assert _me(admin)["push"] is True

    def test_user_off(self, admin):
        _put(admin, {"unread_banner": {"disabled_users": [ME_ID]}})
        assert _me(admin) == {"push": True, "unread_banner": False}
        g = admin.get(f"{BASE_URL}/api/settings/ui-alerts").json()
        assert g["config"]["unread_banner"]["disabled_users"] == [ME_ID]

    def test_invalid_payload_422(self, admin):
        r = admin.put(f"{BASE_URL}/api/settings/ui-alerts", json={"push": {"enabled": "notabool"}})
        assert r.status_code == 422

    def test_nonadmin_403(self, nonadmin):
        assert nonadmin.get(f"{BASE_URL}/api/settings/ui-alerts").status_code == 403
        assert nonadmin.put(f"{BASE_URL}/api/settings/ui-alerts", json={}).status_code == 403
        assert set(_me(nonadmin).keys()) == {"push", "unread_banner"}

    def test_unauth(self):
        r = requests.get(f"{BASE_URL}/api/notifications/ui-alerts/me")
        assert r.status_code in (401, 403)

    def test_restore(self, admin):
        _put(admin, {})
        assert _me(admin) == {"push": True, "unread_banner": True}
