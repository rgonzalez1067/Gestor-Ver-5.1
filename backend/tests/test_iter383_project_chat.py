# Iter383 — Chat interno colaborativo por Proyecto (ACL, RO admin, unread, validaciones)
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
PRJ = "prj_fdb3c4bd1dfc"
CREDS = {
    "rgonzalez": ("rgonzalez@megasoft.com.ve", "MegaSoft2026*"),
    "dcollazo": ("dcollazo@megasoft.com.ve", "MegaSoft2026*"),
    "kherrera": ("kherrera@megasoft.com.ve", "Kherrera2026*Qa"),
    "mmartin": ("mmartin@megasoft.com.ve", "QaMegaSoft2026*x"),
    "jdolande": ("jdolande@megasoft.com.ve", "QaMegaSoft2026*x"),
}
_tokens = {}


def sess(who):
    if who not in _tokens:
        e, p = CREDS[who]
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": e, "password": p})
        if r.status_code != 200 or "session_token" not in r.json():
            pytest.skip(f"login {who} failed: {r.status_code} {r.text[:200]}")
        _tokens[who] = r.json()["session_token"]
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_tokens[who]}"})
    return s


# Summary
class TestSummary:
    def test_admin_summary_shape(self):
        d = sess("rgonzalez").get(f"{BASE_URL}/api/projects-chat/summary").json()
        assert PRJ in d
        assert d[PRJ]["access"] == "rw"
        assert set(d[PRJ].keys()) == {"access", "unread", "total"}
        assert any(v["access"] == "ro" for v in d.values()), "admin should have some ro projects"

    def test_non_participant_user_summary_excludes(self):
        d = sess("mmartin").get(f"{BASE_URL}/api/projects-chat/summary").json()
        assert isinstance(d, dict) and "detail" not in d
        assert PRJ not in d
        assert all(v["access"] == "rw" for v in d.values())


# Access & participants
class TestChatAccess:
    def test_participant_get(self):
        d = sess("rgonzalez").get(f"{BASE_URL}/api/projects/{PRJ}/chat").json()
        assert d["can_write"] is True
        assert "Gerente Comercial" in d["my_roles"]
        roles = {r for p in d["participants"] for r in p["roles"]}
        assert {"Generador", "Gerente Comercial", "Implementador", "Gerente de Implementación"} <= roles
        assert d["project"]["project_number"]
        assert "_id" not in d["project"]

    def test_dcollazo_participant(self):
        d = sess("dcollazo").get(f"{BASE_URL}/api/projects/{PRJ}/chat").json()
        assert d["can_write"] is True
        assert "Gerente de Implementación" in d["my_roles"]

    def test_admin_ro_project(self):
        s = sess("rgonzalez")
        summ = s.get(f"{BASE_URL}/api/projects-chat/summary").json()
        ro = next(pid for pid, v in summ.items() if v["access"] == "ro")
        d = s.get(f"{BASE_URL}/api/projects/{ro}/chat").json()
        assert d["can_write"] is False and d["my_roles"] == []
        r = s.post(f"{BASE_URL}/api/projects/{ro}/chat", json={"text": "TEST_ro"})
        assert r.status_code == 403

    def test_no_module_user_summary_403(self):
        # kherrera has no 'proyectos' module -> blocked by module guard
        assert sess("kherrera").get(f"{BASE_URL}/api/projects-chat/summary").status_code == 403

    def test_non_admin_participant_generador(self):
        d = sess("jdolande").get(f"{BASE_URL}/api/projects/{PRJ}/chat").json()
        assert d["can_write"] is True and "Generador" in d["my_roles"]

    def test_non_participant_403_kherrera(self):
        s = sess("kherrera")
        assert s.get(f"{BASE_URL}/api/projects/{PRJ}/chat").status_code == 403

    def test_non_participant_403(self):
        s = sess("mmartin")
        assert s.get(f"{BASE_URL}/api/projects/{PRJ}/chat").status_code == 403
        assert s.post(f"{BASE_URL}/api/projects/{PRJ}/chat", json={"text": "TEST_x"}).status_code == 403

    def test_empty_text_400(self):
        r = sess("rgonzalez").post(f"{BASE_URL}/api/projects/{PRJ}/chat", json={"text": "   "})
        assert r.status_code == 400

    def test_missing_text_422(self):
        r = sess("rgonzalez").post(f"{BASE_URL}/api/projects/{PRJ}/chat", json={})
        assert r.status_code == 422

    def test_unknown_project_404(self):
        assert sess("rgonzalez").get(f"{BASE_URL}/api/projects/prj_nope000/chat").status_code == 404

    def test_no_auth_401(self):
        assert requests.get(f"{BASE_URL}/api/projects/{PRJ}/chat").status_code == 401


# Unread flow + read receipts
class TestUnreadFlow:
    def test_unread_and_read_receipt(self):
        dc, rg = sess("dcollazo"), sess("rgonzalez")
        rg.get(f"{BASE_URL}/api/projects/{PRJ}/chat")  # mark read baseline
        before = rg.get(f"{BASE_URL}/api/projects-chat/summary").json()[PRJ]
        assert before["unread"] == 0
        r = dc.post(f"{BASE_URL}/api/projects/{PRJ}/chat", json={"text": "TEST_iter383 hola desde dcollazo"})
        assert r.status_code == 200
        m = r.json()
        assert m["message_id"].startswith("pcm_") and m["read_by"] == []
        assert "Gerente de Implementación" in m["roles"]
        after = rg.get(f"{BASE_URL}/api/projects-chat/summary").json()[PRJ]
        assert after["unread"] >= 1 and after["total"] == before["total"] + 1
        # dcollazo own message not unread for himself
        assert dc.get(f"{BASE_URL}/api/projects-chat/summary").json()[PRJ]["unread"] == 0
        # rgonzalez opens → marks read
        rg.get(f"{BASE_URL}/api/projects/{PRJ}/chat")
        assert rg.get(f"{BASE_URL}/api/projects-chat/summary").json()[PRJ]["unread"] == 0
        msgs = dc.get(f"{BASE_URL}/api/projects/{PRJ}/chat").json()["messages"]
        mine = next(x for x in msgs if x["message_id"] == m["message_id"])
        assert len(mine["read_by"]) >= 1
        assert any("Gonz" in n for n in mine["read_by"])
