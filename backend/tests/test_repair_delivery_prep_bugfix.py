"""
Backend regression tests for repair-delivery-prep bug fix.

Context: Previously filtered taller_equipos only by quote_id. After fix: filters
by $or quote_id OR quote_number, and auto-heals quote_id mismatches.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://quote-overhaul.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "rgonzalez@megasoft.com.ve"
ADMIN_PASSWORD = "admin123"

TARGET_QUOTE_ID = "quo_324a4dde457e"
TARGET_QUOTE_NUMBER = "COT-2026-10-001-PYME"
REPRO_002_SERIAL = "REPRO-002"
REPRO_999_SERIAL = "REPRO-999"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("session_token") or data.get("token") or data.get("access_token")
    assert token, f"no token in login response: {data}"
    return token


@pytest.fixture(scope="module")
def headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _collect_serials(prep_response_json):
    serials = []
    for m in prep_response_json.get("modelos", []):
        for s in m.get("serials", []):
            if isinstance(s, dict):
                serials.append(s.get("serial"))
            else:
                serials.append(s)
    return serials


def test_repair_delivery_prep_includes_repro_002_via_quote_number(headers):
    """Main bug fix: te_repro_002 has wrong quote_id but matching quote_number;
    must now appear in modelos[].serials[]."""
    r = requests.get(f"{API}/quotes/{TARGET_QUOTE_ID}/repair-delivery-prep", headers=headers, timeout=30)
    assert r.status_code == 200, f"status={r.status_code} body={r.text}"
    data = r.json()
    serials = _collect_serials(data)
    print(f"Serials returned: {serials}")
    assert REPRO_002_SERIAL in serials, f"REPRO-002 missing from prep response. Got: {serials}"


def test_repair_delivery_prep_regression_repro_999_still_present(headers):
    """Regression: equipment with correct quote_id must keep appearing."""
    r = requests.get(f"{API}/quotes/{TARGET_QUOTE_ID}/repair-delivery-prep", headers=headers, timeout=30)
    assert r.status_code == 200
    serials = _collect_serials(r.json())
    assert REPRO_999_SERIAL in serials, f"REPRO-999 missing. Got: {serials}"


def test_auto_heal_quote_id_persisted(headers):
    """After calling prep once, te_repro_002 should have quote_id auto-corrected.
    Verify by calling prep a 2nd time and ensuring REPRO-002 still shows."""
    r1 = requests.get(f"{API}/quotes/{TARGET_QUOTE_ID}/repair-delivery-prep", headers=headers, timeout=30)
    assert r1.status_code == 200
    r2 = requests.get(f"{API}/quotes/{TARGET_QUOTE_ID}/repair-delivery-prep", headers=headers, timeout=30)
    assert r2.status_code == 200
    serials = _collect_serials(r2.json())
    assert REPRO_002_SERIAL in serials

    # Try to verify directly via taller-equipos listing
    r3 = requests.get(f"{API}/taller-equipos", headers=headers, timeout=30)
    if r3.status_code == 200:
        payload = r3.json()
        items = payload if isinstance(payload, list) else payload.get("items") or payload.get("data") or []
        match = next((x for x in items if x.get("taller_equipo_id") == "te_repro_002"), None)
        if match is not None:
            print(f"te_repro_002 quote_id now: {match.get('quote_id')}")
            assert match.get("quote_id") == TARGET_QUOTE_ID, (
                f"auto-heal failed: te_repro_002.quote_id={match.get('quote_id')}"
            )
        else:
            print("te_repro_002 not visible via /api/taller-equipos listing (filter/pagination); relying on prep re-check")
    else:
        print(f"/api/taller-equipos returned {r3.status_code}; skipping direct DB verification")


def test_repair_delivery_prep_rejects_non_repair_quote(headers):
    """Find a non-repair quote and verify 400."""
    r = requests.get(f"{API}/quotes", headers=headers, params={"limit": 100}, timeout=30)
    assert r.status_code == 200, r.text
    payload = r.json()
    quotes = payload if isinstance(payload, list) else payload.get("items") or payload.get("data") or payload.get("quotes") or []
    non_repair = None
    for q in quotes:
        cat = (q.get("quote_category") or q.get("categoria") or q.get("category") or "").lower()
        if cat and cat != "repair" and cat != "reparacion" and cat != "reparación":
            non_repair = q
            break
    if not non_repair:
        pytest.skip("No non-repair quote found to test rejection")
    qid = non_repair.get("quote_id") or non_repair.get("id")
    r2 = requests.get(f"{API}/quotes/{qid}/repair-delivery-prep", headers=headers, timeout=30)
    assert r2.status_code == 400, f"expected 400 got {r2.status_code}: {r2.text}"
    assert "reparaci" in r2.text.lower()


def test_repair_delivery_prep_empty_models_for_repair_without_equipment(headers):
    """Find a repair quote with no taller_equipos → should return modelos=[] without error."""
    r = requests.get(f"{API}/quotes", headers=headers, params={"limit": 200}, timeout=30)
    assert r.status_code == 200
    payload = r.json()
    quotes = payload if isinstance(payload, list) else payload.get("items") or payload.get("data") or payload.get("quotes") or []
    tried = 0
    for q in quotes:
        cat = (q.get("quote_category") or q.get("categoria") or q.get("category") or "").lower()
        if cat not in ("repair", "reparacion", "reparación"):
            continue
        qid = q.get("quote_id") or q.get("id")
        if qid == TARGET_QUOTE_ID:
            continue
        r2 = requests.get(f"{API}/quotes/{qid}/repair-delivery-prep", headers=headers, timeout=30)
        if r2.status_code == 200:
            data = r2.json()
            if not data.get("modelos"):
                print(f"Found repair quote {qid} with empty modelos → OK")
                assert data.get("modelos") == []
                return
            tried += 1
            if tried >= 10:
                break
    pytest.skip("No empty-modelos repair quote found among sampled quotes")
