# Iter 352: Fase operativa (operational_status) en Cotizaciones / BPC / PDF / Proyectos Directos
import io
import os
import sys
import copy
import pytest
import requests
from pypdf import PdfReader

sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"
BANK_ID = "bnk_91d0cba04375"  # Banco del Tesoro
SQA_PRODUCT = "Cambio Pago Movil "  # Imple originalmente
PROD_PRODUCT = "Tarjetas de Crédito/Débito liquidación en Bs"


def _get_bank(s, bank_id=BANK_ID):
    return next(b for b in s.get(f"{API}/banks").json() if b["bank_id"] == bank_id)


def _pdf_text(content: bytes) -> str:
    r = PdfReader(io.BytesIO(content))
    return "\n".join((p.extract_text() or "") for p in r.pages)


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"})
    if r.status_code != 200:
        pytest.skip("login failed")
    d = r.json()
    sess.headers.update({"Authorization": f"Bearer {d.get('session_token') or d.get('token')}"})
    return sess


@pytest.fixture(scope="module")
def client_id(s):
    r = s.get(f"{API}/clients?limit=1")
    assert r.status_code == 200
    data = r.json()
    data = data if isinstance(data, list) else data.get("clients", [])
    return data[0]["client_id"]


@pytest.fixture(scope="module")
def bank_sqa(s):
    """Pone temporalmente SQA_PRODUCT en SQA y restaura al final."""
    orig = _get_bank(s)
    mod = copy.deepcopy(orig)
    for p in mod["products"]:
        if p["product_name"] == SQA_PRODUCT:
            p["operational_status"] = "SQA"
    r = s.put(f"{API}/banks/{BANK_ID}", json=mod, timeout=30)
    assert r.status_code == 200, r.text
    yield orig
    s.put(f"{API}/banks/{BANK_ID}", json=orig, timeout=30)
    after = _get_bank(s)
    st = {p["product_name"]: p.get("operational_status") for p in after["products"]}
    assert st[SQA_PRODUCT] == "Imple"


@pytest.fixture(scope="module")
def created_quotes(s):
    ids = []
    yield ids
    for q in ids:
        s.delete(f"{API}/quotes/{q}")


# --- BPC medios-pago por banco ---
class TestBPCMediosPago:
    def test_all_phases_returned(self, s, bank_sqa):
        r = s.get(f"{API}/banco-mediopago-condiciones/medios-pago", params={"bank_id": BANK_ID})
        assert r.status_code == 200
        docs = r.json()
        print(docs)
        names = {d["name"].strip().lower(): d.get("operational_status") for d in docs}
        assert all("operational_status" in d for d in docs)
        assert names.get(SQA_PRODUCT.strip().lower()) == "SQA"
        assert "Producción" in names.values()

    def test_without_bank_no_status(self, s):
        r = s.get(f"{API}/banco-mediopago-condiciones/medios-pago")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_bank_with_imple(self, s):
        r = s.get(f"{API}/banco-mediopago-condiciones/medios-pago", params={"bank_id": "bnk_8c250000a996"})
        assert r.status_code == 200
        st = [d["operational_status"] for d in r.json()]
        print(r.json())
        assert "Imple" in st


# --- Unit: with_phase_tag / QuotePDFItem / TemplateQuotePDFRequest / _short_concepto ---
class TestPhaseTagUnits:
    def test_with_phase_tag_idempotent(self):
        from models import with_phase_tag, QuotePDFItem
        assert with_phase_tag("X", "SQA") == "X [SQA]"
        assert with_phase_tag("X [SQA]", "SQA") == "X [SQA]"
        assert with_phase_tag("X", None) == "X"
        it = QuotePDFItem(concepto="Pago C2P", operational_status="SQA")
        assert it.concepto == "Pago C2P [SQA]"
        it2 = QuotePDFItem(**it.model_dump())
        assert it2.concepto == "Pago C2P [SQA]"

    def test_template_pg_items_tag(self):
        from services.pdf_generator import TemplateQuotePDFRequest, _short_concepto
        req = TemplateQuotePDFRequest(cliente_nombre="TEST", pg_setup_items=[
            {"concepto": "Pago C2P (PG)", "costo": 10, "banco": "B", "operational_status": "DESA"},
            {"concepto": "Otro", "costo": 5, "banco": "B"},
        ])
        assert req.pg_setup_items[0]["concepto"] == "Pago C2P (PG) [DESA]"
        assert req.pg_setup_items[1]["concepto"] == "Otro"
        long = "A" * 60 + " [Primer Prod]"
        assert _short_concepto(long).endswith("... [Primer Prod]")


# --- Cotización VPOS: persistencia snapshot + PDF ---
class TestQuotePhaseSnapshot:
    def test_save_and_snapshot_and_pdf(self, s, client_id, bank_sqa, created_quotes):
        payload = {
            "client_id": client_id, "quote_type": "VPOS", "notes": "TEST_phase_tag",
            "services": [
                {"item_type": "additional", "item_name": SQA_PRODUCT, "quantity": 1, "unit_price_usd": 100,
                 "total_usd": 100, "bank_id": BANK_ID, "bank_name": "Banco del Tesoro", "tarifa_setup": 100, "cantidad_cajas": 1, "cantidad_bancos": 1,
                 "operational_status": "SQA"},
                {"item_type": "additional", "item_name": PROD_PRODUCT, "quantity": 1, "unit_price_usd": 50,
                 "total_usd": 50, "bank_id": BANK_ID, "bank_name": "Banco del Tesoro", "tarifa_setup": 50, "cantidad_cajas": 1, "cantidad_bancos": 1,
                 "operational_status": "Producción"},
            ],
        }
        r = s.post(f"{API}/quotes", json=payload)
        assert r.status_code == 200, r.text
        q = r.json()
        created_quotes.append(q["quote_id"])
        g = s.get(f"{API}/quotes/{q['quote_id']}").json()
        st = {x["item_name"]: x.get("operational_status") for x in g["services"]}
        assert st[SQA_PRODUCT] == "SQA" and st[PROD_PRODUCT] == "Producción"

        # Snapshot: cambiar fase en banco a DESA y verificar que la cotización mantiene SQA
        cur = _get_bank(s)
        for p in cur["products"]:
            if p["product_name"] == SQA_PRODUCT:
                p["operational_status"] = "DESA"
        assert s.put(f"{API}/banks/{BANK_ID}", json=cur, timeout=30).status_code == 200
        g2 = s.get(f"{API}/quotes/{q['quote_id']}").json()
        st2 = {x["item_name"]: x.get("operational_status") for x in g2["services"]}
        assert st2[SQA_PRODUCT] == "SQA"

        # Regenerar PDF desde la cotización guardada
        rr = s.post(f"{API}/quotes/{q['quote_id']}/regenerate-pdf", json={}, timeout=90)
        assert rr.status_code == 200, rr.text[:500]
        pdf_url = rr.json()["pdf_url"]
        pr = s.get(f"{API}{pdf_url}", timeout=90)
        assert pr.status_code == 200
        txt = _pdf_text(pr.content)
        print(txt[:3000])
        assert "[SQA]" in txt
        assert "[Producción]" not in txt  # Iter 353: tag Producción omitido

    def test_update_quote_keeps_status(self, s, created_quotes):
        if not created_quotes:
            pytest.skip("no quote")
        qid = created_quotes[0]
        g = s.get(f"{API}/quotes/{qid}").json()
        r = s.put(f"{API}/quotes/{qid}", json={"client_id": g["client_id"], "quote_type": "VPOS",
                                                "services": g["services"], "notes": "TEST_phase_tag upd"})
        assert r.status_code == 200, r.text[:300]
        g2 = s.get(f"{API}/quotes/{qid}").json()
        assert any(x.get("operational_status") == "SQA" for x in g2["services"])


# --- PDF desde frontend (generate-pdf-with-template) ---
class TestTemplatePDF:
    def test_vpos_pdf_contains_tags(self, s, client_id):
        body = {
            "cliente_nombre": "TEST_Cliente", "client_id": client_id, "quote_type": "VPOS",
            "setup_items": [{"concepto": "Pago C2P - Banesco", "tarifa": 100, "total": 100, "operational_status": "SQA",
                             "bank_name": "Banesco"}],
            "additional_items": [{"concepto": "Pago C2P", "tarifa": 100, "total": 100, "operational_status": "SQA",
                                  "bank_name": "Banesco"},
                                 {"concepto": "Debito Inmediato", "tarifa": 100, "total": 100,
                                  "operational_status": "Producción", "bank_name": "Banesco"}],
        }
        r = s.post(f"{API}/quotes/generate-pdf-with-template", json=body, timeout=90)
        assert r.status_code == 200, r.text[:500]
        txt = _pdf_text(r.content)
        assert "[SQA]" in txt

    def test_pg_pdf_contains_tags(self, s, client_id):
        body = {
            "cliente_nombre": "TEST_Cliente", "client_id": client_id, "quote_type": "GATEWAY",
            "template_type": "payment_gateway",
            "pg_setup_items": [{"concepto": "Pago C2P (PG)", "costo": 100, "banco": "Banesco", "observacion": "",
                                "operational_status": "Primer Prod"}],
        }
        r = s.post(f"{API}/quotes/generate-pdf-with-template", json=body, timeout=90)
        assert r.status_code == 200, r.text[:500]
        txt = _pdf_text(r.content)
        print(txt[:2000])
        assert "[Primer Prod]" in txt


# --- Proyectos Directos _grid_to_services ---
class TestDirectProjectGrid:
    def test_grid_to_services_keeps_status(self):
        from routes.direct_projects import _grid_to_services
        out = _grid_to_services([
            {"bank_name": "B", "product_name": "P1", "quantity": 2, "operational_status": "SQA"},
            {"bank_name": "B", "product_name": "P1", "quantity": 1},
            {"bank_name": "B", "product_name": "P2", "quantity": 1, "operational_status": "Producción"},
        ])
        d = {o["item_name"]: o for o in out}
        assert d["P1"]["quantity"] == 3 and d["P1"]["operational_status"] == "SQA"
        assert d["P2"]["operational_status"] == "Producción"
