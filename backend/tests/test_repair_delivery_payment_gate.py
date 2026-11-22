"""Backend tests for Repair Delivery payment gate (prep + deliver).

Covers:
- GET /api/quotes/{id}/repair-delivery-prep → delivery_mode / payment_validated / block_message
- POST /api/quotes/{id}/repair-deliver blocked (400), warning+confirm (428→200+legend),
  normal (200 no legend), irregular exception (200 with legend).
- Regression: non-repair quote → 400; delivered serial drops out of prep.

Fixtures (pre-seeded in preview DB):
  cli_test_repair, quo_test_rep_a/b/c, te_test_rep_a1/b1/c1
"""

import os
import time
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gestor-proyectos-4--5tifwbuw.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "rgonzalez@megasoft.com.ve"
ADMIN_PASS = "admin123"

LEGEND = "Equipos se estan entregando sin haberse recibido y validado el correspondiente pago"
BLOCK_FRAGMENT = "No es posible generar la Nota de Entrega"
UPLOADS_DIR = Path("/app/backend/uploads")

NON_REPAIR_QUOTE_ID = "quo_b8b81ce5405c"  # fast_track quote (pre-existing)


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _pdf_text(url_from_response: str) -> str:
    """Load the generated PDF from UPLOADS_DIR and return its text."""
    if not url_from_response:
        return ""
    fname = url_from_response.replace("/uploads/", "").lstrip("/")
    p = UPLOADS_DIR / fname
    if not p.exists():
        return ""
    try:
        import pdfplumber
        with pdfplumber.open(str(p)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception:
        try:
            from pypdf import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader(str(p)).pages)
        except Exception:
            return ""


# ---------- 1. PREP modes ----------
@pytest.mark.order(0)
class TestPrepModes:
    def test_prep_warning_a(self, auth):
        r = requests.get(f"{BASE_URL}/api/quotes/quo_test_rep_a/repair-delivery-prep",
                         headers=auth, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["delivery_mode"] == "warning"
        assert d["payment_validated"] is False
        assert d["block_message"] == ""
        assert d["quote_status"] == "Reparada"
        serials = [s["taller_equipo_id"] for m in d["modelos"] for s in m["serials"]]
        assert "te_test_rep_a1" in serials

    def test_prep_normal_b(self, auth):
        r = requests.get(f"{BASE_URL}/api/quotes/quo_test_rep_b/repair-delivery-prep",
                         headers=auth, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["delivery_mode"] == "normal"
        assert d["payment_validated"] is True
        assert d["block_message"] == ""

    def test_prep_blocked_c(self, auth):
        r = requests.get(f"{BASE_URL}/api/quotes/quo_test_rep_c/repair-delivery-prep",
                         headers=auth, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["delivery_mode"] == "blocked"
        assert d["payment_validated"] is False
        assert BLOCK_FRAGMENT in d["block_message"]


# ---------- 2. BLOCKED deliver (no exception header) ----------
class TestBlockedDeliver:
    def test_c_without_exception_returns_400(self, auth):
        r = requests.post(
            f"{BASE_URL}/api/quotes/quo_test_rep_c/repair-deliver",
            headers=auth,
            json={
                "selected_serials": ["te_test_rep_c1"],
                "delivery_method": "personalizada",
                "receiver_name": "QA Blocker",
                "receiver_cedula": "V-000",
                "receiver_phone": "04140000000",
                "invoice_number": "F-TEST-BLOCK",
            },
            timeout=60,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        assert BLOCK_FRAGMENT in r.text


# ---------- 3. WARNING + legend ----------
# These two must run in order; the second depends on the 428 of the first.
class TestWarningConfirmFlow:
    @pytest.mark.order(1)
    def test_a_without_confirm_returns_428(self, auth):
        r = requests.post(
            f"{BASE_URL}/api/quotes/quo_test_rep_a/repair-deliver",
            headers=auth,
            json={
                "selected_serials": ["te_test_rep_a1"],
                "delivery_method": "personalizada",
                "receiver_name": "QA Tester",
                "receiver_cedula": "V-123",
                "receiver_phone": "04140000000",
                "invoice_number": "F-TEST-001",
                "notes": "Prueba QA",
            },
            timeout=60,
        )
        assert r.status_code == 428, f"expected 428, got {r.status_code}: {r.text}"
        # FastAPI wraps detail
        try:
            detail = r.json().get("detail", "")
        except Exception:
            detail = r.text
        assert detail.startswith("UNPAID_CONFIRM:"), f"unexpected detail: {detail}"

    @pytest.mark.order(2)
    def test_a_with_confirm_delivers_and_injects_legend(self, auth):
        r = requests.post(
            f"{BASE_URL}/api/quotes/quo_test_rep_a/repair-deliver",
            headers=auth,
            json={
                "selected_serials": ["te_test_rep_a1"],
                "delivery_method": "personalizada",
                "receiver_name": "QA Tester",
                "receiver_cedula": "V-123",
                "receiver_phone": "04140000000",
                "invoice_number": "F-TEST-001",
                "notes": "Prueba QA",
                "confirm_unpaid_delivery": True,
            },
            timeout=120,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("equipos_entregados") == 1
        pdf_url = data.get("hoja_ruta_url")
        # legend must be inside the generated PDF notes section
        text = _pdf_text(pdf_url) if pdf_url else ""
        assert LEGEND in text, (
            f"legend not found in PDF ({pdf_url}). "
            f"first 400 chars: {text[:400]!r}"
        )

    @pytest.mark.order(3)
    def test_a_prep_after_delivery_is_empty(self, auth):
        # Allow a brief moment for persistence
        time.sleep(1)
        r = requests.get(f"{BASE_URL}/api/quotes/quo_test_rep_a/repair-delivery-prep",
                         headers=auth, timeout=30)
        assert r.status_code == 200
        d = r.json()
        serials = [s["taller_equipo_id"] for m in d["modelos"] for s in m["serials"]]
        assert "te_test_rep_a1" not in serials, f"delivered serial still present: {serials}"
        # quote should be Entregada and entrega_completa true
        assert d["entrega_completa"] is True
        assert d["quote_status"] in ("Entregada", "Entregado")


# ---------- 4. NORMAL deliver (payment validated) ----------
class TestNormalDeliver:
    def test_b_direct_200_no_legend(self, auth):
        r = requests.post(
            f"{BASE_URL}/api/quotes/quo_test_rep_b/repair-deliver",
            headers=auth,
            json={
                "selected_serials": ["te_test_rep_b1"],
                "delivery_method": "personalizada",
                "receiver_name": "QA Tester",
                "receiver_cedula": "V-124",
                "receiver_phone": "04140000000",
                "invoice_number": "F-TEST-002",
                "notes": "",
            },
            timeout=120,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("equipos_entregados") == 1
        pdf_url = data.get("hoja_ruta_url")
        text = _pdf_text(pdf_url) if pdf_url else ""
        assert LEGEND not in text, f"legend unexpectedly present in NORMAL PDF ({pdf_url})"


# ---------- 5. IRREGULAR exception valve on blocked quote ----------
class TestIrregularException:
    def test_c_with_exception_headers_200_with_legend(self, auth):
        headers = {
            **auth,
            "x-exception-reason": "Prueba excepcion QA",
            "x-regularization-date": "2026-09-20",
        }
        r = requests.post(
            f"{BASE_URL}/api/quotes/quo_test_rep_c/repair-deliver",
            headers=headers,
            json={
                "selected_serials": ["te_test_rep_c1"],
                "delivery_method": "personalizada",
                "receiver_name": "QA Tester",
                "receiver_cedula": "V-125",
                "receiver_phone": "04140000000",
                "invoice_number": "F-TEST-003",
            },
            timeout=120,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("equipos_entregados") == 1
        pdf_url = data.get("hoja_ruta_url")
        text = _pdf_text(pdf_url) if pdf_url else ""
        assert LEGEND in text, (
            f"legend missing in irregular-exception PDF ({pdf_url}). "
            f"first 400 chars: {text[:400]!r}"
        )


# ---------- 6. Non-repair quote → 400 ----------
class TestNonRepairQuote:
    def test_prep_rejects_non_repair(self, auth):
        r = requests.get(f"{BASE_URL}/api/quotes/{NON_REPAIR_QUOTE_ID}/repair-delivery-prep",
                         headers=auth, timeout=30)
        assert r.status_code == 400, r.text
        assert "solo aplica a cotizaciones de reparación" in r.text

    def test_deliver_rejects_non_repair(self, auth):
        r = requests.post(f"{BASE_URL}/api/quotes/{NON_REPAIR_QUOTE_ID}/repair-deliver",
                          headers=auth, json={"selected_serials": []}, timeout=30)
        assert r.status_code == 400, r.text
        assert "solo aplica a cotizaciones de reparación" in r.text
