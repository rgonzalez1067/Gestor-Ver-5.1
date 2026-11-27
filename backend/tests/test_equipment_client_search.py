# Equipment quote wizard client selector: /api/clients/search by legal_name, fantasy_name, RIF, special regex chars
import os, requests, pytest
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

@pytest.fixture(scope="module")
def h():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"})
    if r.status_code != 200: pytest.skip("login failed")
    return {"Authorization": f"Bearer {r.json()['session_token']}"}

def s(h, q):
    r = requests.get(f"{BASE_URL}/api/clients/search", params={"q": q, "include_placeholder": "true"}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()

def ids(res, rif): return [c for c in res if c["rif"] == rif]

def test_legal_name(h): assert ids(s(h, "WORLD TOYS"), "J504419613")
def test_legal_name_with_ca(h): assert ids(s(h, "TOYS VAL, C.A."), "J504419613")
def test_fantasy_name(h): assert ids(s(h, "REDU"), "J504419613")
def test_fantasy_name_partial_accent(h): assert ids(s(h, "Brasero El"), "J501546010")
def test_rif_with_dashes(h): assert ids(s(h, "J-50441961-3"), "J504419613")
def test_rif_without_dashes(h): assert ids(s(h, "J504419613"), "J504419613")
def test_lowercase_legal(h): assert ids(s(h, "inversiones salus"), "J501546010")
@pytest.mark.parametrize("q", ["C.A.", "S.A.)", "((", "[abc", "*+?", "a|b", "\\\\", "$^"])
def test_special_chars_no_500(h, q): s(h, q)
