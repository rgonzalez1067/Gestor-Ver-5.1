"""Iter363 — PG con Tokenizador / Link de Pago (flags) + LINK_PAGO standalone (sin PG).
Valida preview-pdf-with-template, create-with-pdf, regenerate-pdf, PUT persistencia y tokenizador-billing-line.
"""
import io
import os
import pytest
import requests
from PyPDF2 import PdfReader

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}
PYME_CLIENT = "cli_883fcd784734"  # EKONOMAR, C.A. (PYME)
INTEGRATOR = "int_a54da953c960"
PG_SETUP = [{"concepto": "Persona Jurídica", "costo": 240, "banco": "N/A"},
            {"concepto": "C2P (PG)", "costo": 36, "banco": "Banco X"}]
CREATED = []


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    tok = r.json().get("session_token") or r.json().get("token") or r.json().get("access_token")
    if tok:
        ses.headers.update({"Authorization": f"Bearer {tok}"})
    yield ses
    for qid in CREATED:
        ses.delete(f"{BASE_URL}/api/quotes/{qid}", timeout=30)


def txt_of(content):
    rd = PdfReader(io.BytesIO(content))
    pages = [(p.extract_text() or "") for p in rd.pages]
    return pages, "\n".join(pages)


def pdf_data(qt="GATEWAY", seg="PYME", **kw):
    d = dict(quote_type=qt, client_id=PYME_CLIENT, cliente_nombre="TEST_Cli", cliente_rif="J1",
             integrator_id=INTEGRATOR, integrator_name="Integ", integrator_app_name="App",
             template_type="payment_gateway", client_segment=seg,
             pg_setup_items=PG_SETUP if qt == "GATEWAY" or not kw.get("lp_standalone") else [])
    d.update(kw)
    return d


def preview(s, **kw):
    r = s.post(f"{BASE_URL}/api/quotes/preview-pdf-with-template", json=pdf_data(**kw), timeout=90)
    assert r.status_code == 200, r.text[:300]
    return txt_of(r.content)


def tok_pos(pages, needle):
    return next((i for i, p in enumerate(pages) if needle in p), -1)


# ---- Preview PDF (PG flags) ----
@pytest.mark.parametrize("tok,link", [(False, False), (True, False), (False, True), (True, True)])
def test_preview_pg_flags(s, tok, link):
    pages, t = preview(s, include_tokenizador=tok, include_link_pago=link)
    assert "INVERSIÓN EN SETUP" in t
    assert ("Tarifa del Tokenizador" in t) == tok
    assert ("Tarifas de Link de Pago" in t) == link
    terms = tok_pos(pages, "TÉRMINOS DE LA COTIZACIÓN")
    assert terms >= 0
    if tok:
        assert tok_pos(pages, "Tarifa del Tokenizador") < terms
    if link:
        assert tok_pos(pages, "Tarifas de Link de Pago") < terms


def test_preview_pg_corp_both(s):
    pages, t = preview(s, seg="CORP", include_tokenizador=True, include_link_pago=True)
    assert "Tarifa del Tokenizador" in t and "Tarifas de Link de Pago" in t and "INVERSIÓN EN SETUP" in t


# ---- Preview LP standalone ----
@pytest.mark.parametrize("variant,tok,link", [("ambos", True, True), ("tokenizador", True, False), ("link_pago", False, True)])
def test_preview_lp_standalone(s, variant, tok, link):
    pages, t = preview(s, qt="LINK_PAGO", link_pago_variant=variant, lp_standalone=True)
    assert "INVERSIÓN EN SETUP" not in t
    assert "Persona Jurídica" not in t
    assert "SERVICIOS COTIZADOS" in t
    assert ("Tarifa del Tokenizador" in t) == tok
    assert ("Tarifas de Link de Pago" in t) == link
    assert "TÉRMINOS DE LA COTIZACIÓN" in t


def test_preview_lp_legacy_keeps_pg(s):
    pages, t = preview(s, qt="LINK_PAGO", link_pago_variant="ambos", lp_standalone=False)
    assert "INVERSIÓN EN SETUP" in t and "Tarifa del Tokenizador" in t


def test_preview_vpos_regression(s):
    r = s.post(f"{BASE_URL}/api/quotes/preview-pdf-with-template",
               json=dict(quote_type="VPOS", client_id=PYME_CLIENT, cliente_nombre="TEST", template_type="vpos_pyme",
                         setup_items=[{"concepto": "Setup", "cantidad_cajas": 1, "cantidad_bancos": 1, "tarifa": 100}]),
               timeout=90)
    assert r.status_code == 200
    _, t = txt_of(r.content)
    assert "Tarifa del Tokenizador" not in t and "Tarifas de Link de Pago" not in t


# ---- create-with-pdf + GET + saved PDF + regenerate + billing line ----
def create(s, qt, **kw):
    pd = pdf_data(qt=qt, **{k: v for k, v in kw.items() if k in ("link_pago_variant", "lp_standalone", "include_tokenizador", "include_link_pago")})
    body = dict(client_id=PYME_CLIENT, quote_category="implementation", quote_type=qt,
                integrator_id=INTEGRATOR, integrator_name="Integ", integrator_app_name="App",
                notes="TEST_iter363", client_segment="PYME", pdf_data=pd,
                pg_setup_items=pd["pg_setup_items"], **kw)
    r = s.post(f"{BASE_URL}/api/quotes/create-with-pdf", json=body, timeout=120)
    assert r.status_code == 200, r.text[:300]
    j = r.json()
    CREATED.append(j["quote"]["quote_id"])
    return j


def fetch_pdf(s, url):
    r = s.get(f"{BASE_URL}/api{url}", timeout=60)
    assert r.status_code == 200, f"{url} -> {r.status_code}"
    return txt_of(r.content)


def test_create_pg_both_flags_persist_and_pdf(s):
    j = create(s, "GATEWAY", include_tokenizador=True, include_link_pago=True)
    qid = j["quote"]["quote_id"]
    assert j["pdf_url"]
    g = s.get(f"{BASE_URL}/api/quotes/{qid}", timeout=30).json()
    assert g["include_tokenizador"] is True and g["include_link_pago"] is True
    assert float(g["total_usd"]) == 276.0
    _, t = fetch_pdf(s, j["pdf_url"])
    assert "INVERSIÓN EN SETUP" in t and "Tarifa del Tokenizador" in t and "Tarifas de Link de Pago" in t
    bl = s.get(f"{BASE_URL}/api/quotes/{qid}/tokenizador-billing-line", timeout=30).json()
    assert bl["applies"] is True
    # regenerate uses stored flags
    rg = s.post(f"{BASE_URL}/api/quotes/{qid}/regenerate-pdf", json={}, timeout=120)
    assert rg.status_code == 200, rg.text[:300]
    _, t2 = fetch_pdf(s, rg.json()["pdf_url"])
    assert "Tarifa del Tokenizador" in t2 and "Tarifas de Link de Pago" in t2 and "INVERSIÓN EN SETUP" in t2
    # PUT update: turn off link, keep tok
    up = s.put(f"{BASE_URL}/api/quotes/{qid}", json={"include_link_pago": False}, timeout=30)
    assert up.status_code == 200, up.text[:300]
    g2 = s.get(f"{BASE_URL}/api/quotes/{qid}", timeout=30).json()
    assert g2["include_tokenizador"] is True and g2["include_link_pago"] is False


def test_create_pg_tok_only_billing_and_pg_no_flags(s):
    j = create(s, "GATEWAY", include_tokenizador=False, include_link_pago=True)
    qid = j["quote"]["quote_id"]
    bl = s.get(f"{BASE_URL}/api/quotes/{qid}/tokenizador-billing-line", timeout=30).json()
    assert bl["applies"] is False
    _, t = fetch_pdf(s, j["pdf_url"])
    assert "Tarifas de Link de Pago" in t and "Tarifa del Tokenizador" not in t


def test_create_lp_standalone_ambos(s):
    j = create(s, "LINK_PAGO", link_pago_variant="ambos", lp_standalone=True)
    qid = j["quote"]["quote_id"]
    g = s.get(f"{BASE_URL}/api/quotes/{qid}", timeout=30).json()
    assert g["lp_standalone"] is True and g["quote_type"] == "LINK_PAGO"
    assert g["pg_setup_items"] == [] and float(g["total_usd"]) == 0
    assert j["pdf_url"], "PDF should be generated for standalone"
    _, t = fetch_pdf(s, j["pdf_url"])
    assert "INVERSIÓN EN SETUP" not in t and "Persona Jurídica" not in t
    assert "Tarifa del Tokenizador" in t and "Tarifas de Link de Pago" in t
    rg = s.post(f"{BASE_URL}/api/quotes/{qid}/regenerate-pdf", json={}, timeout=120)
    assert rg.status_code == 200
    _, t2 = fetch_pdf(s, rg.json()["pdf_url"])
    assert "INVERSIÓN EN SETUP" not in t2 and "Tarifa del Tokenizador" in t2
    bl = s.get(f"{BASE_URL}/api/quotes/{qid}/tokenizador-billing-line", timeout=30).json()
    assert bl["applies"] is True


def test_create_lp_legacy_regenerate_keeps_pg(s):
    j = create(s, "LINK_PAGO", link_pago_variant="tokenizador", lp_standalone=False)
    qid = j["quote"]["quote_id"]
    rg = s.post(f"{BASE_URL}/api/quotes/{qid}/regenerate-pdf", json={}, timeout=120)
    assert rg.status_code == 200
    _, t = fetch_pdf(s, rg.json()["pdf_url"])
    assert "INVERSIÓN EN SETUP" in t and "Tarifa del Tokenizador" in t


def test_preview_lp_standalone_corp(s):
    pages, t = preview(s, qt="LINK_PAGO", seg="CORP", link_pago_variant="ambos", lp_standalone=True)
    assert "INVERSIÓN EN SETUP" not in t and "Persona Jurídica" not in t
    assert "Tarifa del Tokenizador" in t and "Tarifas de Link de Pago" in t
