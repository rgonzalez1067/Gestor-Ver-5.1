# Iter374: reassign a TEST clone project and verify timeline adds a new tramo (clone deleted after)
import os
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
SRC = "prj_92fe734eb1f1"
CLONE = "prj_test374_tl01"


def _db_run(coro_fn):
    async def run():
        cli = AsyncIOMotorClient(os.environ['MONGO_URL'])
        try:
            return await coro_fn(cli[os.environ['DB_NAME']])
        finally:
            cli.close()
    return asyncio.run(run())


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    if r.status_code != 200:
        pytest.skip("login failed")
    ses.headers.update({"Authorization": f"Bearer {r.json()['session_token']}"})
    ses.me = r.json().get("user", {})
    return ses


@pytest.fixture(scope="module")
def clone():
    async def mk(db):
        p = await db.projects.find_one({"project_id": SRC}, {"_id": 0})
        p["project_id"] = CLONE
        p["project_number"] = "TEST_374_TL"
        p["client_name"] = "TEST_374 " + (p.get("client_name") or "")
        await db.projects.delete_one({"project_id": CLONE})
        await db.projects.insert_one(p)
    _db_run(mk)
    yield CLONE
    _db_run(lambda db: db.projects.delete_one({"project_id": CLONE}))


def test_reassign_adds_tramo(s, clone):
    before = s.get(f"{BASE_URL}/api/projects/{clone}/assignment-timeline").json()["timeline"]
    assert len(before) == 2
    me_id = s.me.get("user_id")
    assert me_id
    r = s.put(f"{BASE_URL}/api/projects/{clone}/assign", json={"assigned_to_user_id": me_id, "reassignment_comment": "TEST_374"})
    assert r.status_code == 200, r.text
    after = s.get(f"{BASE_URL}/api/projects/{clone}/assignment-timeline").json()["timeline"]
    print(after)
    assert len(after) == 3
    assert after[2]["current"] and after[2]["days"] == 0 and after[2]["until"] is None
    assert after[2]["name"] == r.json()["assigned_to"]
    assert not after[1]["current"] and after[1]["until"] == after[2]["at"]
    assert "Rosdely" in after[1]["name"]
    # restore = clone is deleted in fixture teardown (avoid notifying real implementers)


def test_source_untouched(s):
    tl = s.get(f"{BASE_URL}/api/projects/{SRC}/assignment-timeline").json()["timeline"]
    assert len(tl) == 2
