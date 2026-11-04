"""iter350 — Historial de Correos (GET /api/email-logs filtros+paginación, /email-logs/actions) y
endpoints de Contingencia usados por Centro de Respaldos (counts/page/attachments-list). Solo lectura."""
import os
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env", override=False)

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/') + '/api'
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"}
NONADMIN = {"email": "kherrera@megasoft.com.ve", "password": "Test1234!"}


def _db_count(q=None):
    async def f():
        c = AsyncIOMotorClient(os.environ['MONGO_URL'])
        try:
            return await c[os.environ['DB_NAME']].email_logs.count_documents(q or {})
        finally:
            c.close()
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(f())
    finally:
        loop.close()


def _login(creds):
    r = requests.post(f"{BASE_URL}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed {creds['email']}: {r.status_code}")
    t = r.json().get("session_token") or r.json().get("token")
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def H():
    return _login(ADMIN)


def _get(H, **params):
    return requests.get(f"{BASE_URL}/email-logs", headers=H, params=params, timeout=60)


# --- Email logs: totals & pagination
class TestEmailLogs:
    def test_unauth(self):
        r = requests.get(f"{BASE_URL}/email-logs", timeout=30)
        assert r.status_code in (401, 403)

    def test_total_db_matches_count(self, H):
        r = _get(H, page=1, limit=25)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_db"] == _db_count()
        assert d["total"] == d["total_db"]
        assert d["limit"] == 25 and d["page"] == 1
        assert d["pages"] == -(-d["total"] // 25)
        assert len(d["email_logs"]) == 25
        for l in d["email_logs"]:
            assert "_id" not in l and "html" not in l
        dates = [l["created_at"] for l in d["email_logs"]]
        assert dates == sorted(dates, reverse=True)

    def test_pagination_distinct_pages(self, H):
        p1 = {l["email_log_id"] for l in _get(H, page=1, limit=25).json()["email_logs"]}
        p2 = {l["email_log_id"] for l in _get(H, page=2, limit=25).json()["email_logs"]}
        assert p1 and p2 and not (p1 & p2)

    def test_last_page(self, H):
        d = _get(H, page=1, limit=25).json()
        last = _get(H, page=d["pages"], limit=25).json()
        assert 0 < len(last["email_logs"]) <= 25
        beyond = _get(H, page=d["pages"] + 1, limit=25).json()
        assert beyond["email_logs"] == []

    def test_limit_clamped(self, H):
        d = _get(H, page=1, limit=5000).json()
        assert d["limit"] == 200 and len(d["email_logs"]) == 200

    def test_status_filter(self, H):
        for st in ("sent", "error", "simulated", "queued"):
            d = _get(H, status=st, limit=25).json()
            assert d["total"] == _db_count({"status": st})
            assert all(l["status"] == st for l in d["email_logs"])
            assert d["total_db"] == _db_count()

    def test_action_filter(self, H):
        acts = requests.get(f"{BASE_URL}/email-logs/actions", headers=H, timeout=30).json()
        assert isinstance(acts["actions"], list) and len(acts["actions"]) > 0
        assert set(acts["statuses"]) <= {"sent", "error", "queued", "simulated"}
        a = acts["actions"][0]
        d = _get(H, action=a, limit=25).json()
        assert d["total"] == _db_count({"action": a}) and d["total"] > 0
        assert all(l["action"] == a for l in d["email_logs"])

    def test_date_filter(self, H):
        d = _get(H, date_from="2026-01-01", date_to="2026-01-31", limit=200).json()
        assert d["total"] == _db_count({"created_at": {"$gte": "2026-01-01", "$lt": "2026-02-01"}})
        for l in d["email_logs"]:
            assert "2026-01-01" <= l["created_at"][:10] <= "2026-01-31"
        # inclusive single-day
        latest = _get(H, limit=1).json()["email_logs"][0]["created_at"][:10]
        d2 = _get(H, date_from=latest, date_to=latest).json()
        assert d2["total"] >= 1

    def test_to_and_subject_filter_case_insensitive(self, H):
        sample = _get(H, limit=1).json()["email_logs"][0]
        to = sample["to"][0] if isinstance(sample["to"], list) else sample["to"]
        d = _get(H, to=to.upper()[:8]).json()
        assert d["total"] >= 1
        word = (sample.get("subject") or "x")[:10].lower()
        d2 = _get(H, subject=word).json()
        assert d2["total"] >= 1
        assert all(word in (l.get("subject") or "").lower() for l in d2["email_logs"])

    def test_regex_special_chars_safe(self, H):
        r = _get(H, subject="(([[*+?")
        assert r.status_code == 200 and r.json()["total"] == 0

    def test_combined_filters(self, H):
        d = _get(H, status="sent", action="bank_mass_communication", limit=25).json()
        assert d["total"] == _db_count({"status": "sent", "action": "bank_mass_communication"})

    def test_invalid_date_returns_4xx(self, H):
        r = _get(H, date_to="not-a-date")
        assert r.status_code in (400, 422), f"got {r.status_code}"

    def test_nonadmin_access(self):
        h = _login(NONADMIN)
        r = requests.get(f"{BASE_URL}/email-logs", headers=h, params={"limit": 1}, timeout=30)
        print("non-admin /email-logs status:", r.status_code)
        assert r.status_code in (200, 403)


# --- Contingency endpoints used by Backup Center buttons
class TestContingency:
    def test_counts(self, H):
        r = requests.get(f"{BASE_URL}/admin/quotes-bundle-migration/counts", headers=H, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["collections"], list) and d["collections"]
        assert all(c in d["counts"] for c in d["collections"])

    def test_page(self, H):
        c = requests.get(f"{BASE_URL}/admin/quotes-bundle-migration/counts", headers=H, timeout=60).json()
        col = c["collections"][0]
        r = requests.get(f"{BASE_URL}/admin/quotes-bundle-migration/page", headers=H,
                         params={"collection": col, "skip": 0, "limit": 5}, timeout=60)
        assert r.status_code == 200
        assert len(r.json()["docs"]) == min(5, c["counts"][col])

    def test_attachments_list_and_one(self, H):
        r = requests.get(f"{BASE_URL}/admin/quotes-bundle-migration/attachments-list", headers=H, timeout=120)
        assert r.status_code == 200
        items = r.json().get("items", [])
        print("attachments:", len(items))
        if items:
            a = requests.get(f"{BASE_URL}/admin/quotes-bundle-migration/attachment", headers=H,
                             params={"path": items[0]["path"]}, timeout=60)
            assert a.status_code in (200, 404)

    def test_nonadmin_forbidden(self):
        h = _login(NONADMIN)
        r = requests.get(f"{BASE_URL}/admin/quotes-bundle-migration/counts", headers=h, timeout=30)
        assert r.status_code in (401, 403)
