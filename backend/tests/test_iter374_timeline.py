# Iter374: assignment timeline endpoint + reassignment adds tramo; sponsor banks logos
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
PID = "prj_92fe734eb1f1"


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    ses.headers.update({"Authorization": f"Bearer {r.json()['session_token']}"})
    return ses


# Timeline for reference project
def test_timeline_reference(s):
    r = s.get(f"{BASE_URL}/api/projects/{PID}/assignment-timeline")
    assert r.status_code == 200, r.text
    tl = r.json()["timeline"]
    print(tl)
    assert len(tl) == 2
    assert "Omar" in tl[0]["name"] and not tl[0]["current"]
    assert 25 <= tl[0]["days"] <= 29
    assert "Rosdely" in tl[1]["name"] and tl[1]["current"] and tl[1]["until"] is None
    assert tl[0]["until"] == tl[1]["at"]


def test_timeline_404(s):
    r = s.get(f"{BASE_URL}/api/projects/prj_doesnotexist/assignment-timeline")
    assert r.status_code == 404


def test_timeline_unauth():
    r = requests.get(f"{BASE_URL}/api/projects/{PID}/assignment-timeline")
    assert r.status_code in (401, 403)


# Bank logos referenced by sponsored quotes load
def test_sponsor_bank_logos(s):
    banks = s.get(f"{BASE_URL}/api/banks")
    assert banks.status_code == 200
    bl = banks.json() if isinstance(banks.json(), list) else banks.json().get("banks", [])
    by = {b["bank_id"]: b for b in bl}
    qr = s.get(f"{BASE_URL}/api/quotes")
    assert qr.status_code == 200
    qs = qr.json() if isinstance(qr.json(), list) else qr.json().get("quotes", qr.json().get("items", []))
    sp = [q for q in qs if q.get("sponsored_implementation")]
    print("sponsored:", len(sp), "with processor:", [q["quote_id"] for q in sp if q.get("sponsoring_processor_id")])
    assert sp
    urls = set()
    for q in sp:
        for k in ("sponsoring_bank_id", "sponsoring_processor_id"):
            b = by.get(q.get(k))
            if b and b.get("bank_logo_url"):
                urls.add(b["bank_logo_url"])
            elif q.get(k):
                print("NO LOGO for", k, q.get(k), q["quote_id"])
    for u in urls:
        r = requests.get(f"{BASE_URL}{u}")
        print(u, r.status_code, r.headers.get("content-type"))
        assert r.status_code == 200 and "image" in r.headers.get("content-type", "")
