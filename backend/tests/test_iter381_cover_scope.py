# Iter 381: PDF cover hierarchy (Sucursal Beneficiaria, Alcance de la Cotización, Varios RIF) + regenerate-pdf
import os, io, requests, pytest, fitz

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/') or open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0].rstrip('/')
MULTI_QID = "quo_bad7112f40ba"
BRANCH_CID = "cli_dc77d71c6d98"


@pytest.fixture(scope="module")
def s():
    ss = requests.Session()
    r = ss.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip("login failed")
    ss.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    return ss


def pages(content):
    doc = fitz.open(stream=content, filetype="pdf")
    return [p.get_text() for p in doc]


def base_payload(**kw):
    p = {"cliente_nombre": "X", "quote_type": "GATEWAY", "template_type": "gateway_pyme", "quote_number": "TEST_COT-381",
         "pg_setup_items": [{"concepto": "Setup PG", "costo": 100, "banco": "", "observacion": ""}]}
    p.update(kw)
    return p


def norm(t):
    return " ".join(t.split()).upper()


class TestCoverPdf:
    def test_branch_client_sucursal_beneficiaria(self, s):
        r = s.post(f"{BASE_URL}/api/quotes/generate-pdf-with-template", json=base_payload(client_id=BRANCH_CID))
        assert r.status_code == 200, r.text[:300]
        p1 = norm(pages(r.content)[0])
        print(p1[:1500])
        assert "SUCURSAL BENEFICIARIA" in p1
        assert "PARAMO CARICUAO" in p1
        assert "INVERSIONES COLD 2024" in p1
        assert "ALCANCE DE LA COTIZACI" not in p1

    def test_principal_client_no_sucursal_row(self, s):
        r = s.post(f"{BASE_URL}/api/quotes/generate-pdf-with-template", json=base_payload(client_id="cli_a88bb320f1a9"))
        assert r.status_code == 200
        p1 = norm(pages(r.content)[0])
        assert "SUCURSAL BENEFICIARIA" not in p1

    def test_multirif_distribution_scope_block(self, s):
        dist = [{"client_id": f"c{i}", "rif": f"J5000000{i}0", "client_name": f"TEST_RAZON {i}", "marca_name": "MARCA_A" if i < 2 else "MARCA_B",
                 "boxes": 1, "stores": [{"name": "Principal", "boxes": 1}, {"name": f"Suc {i}", "boxes": 1}]} for i in range(4)]
        r = s.post(f"{BASE_URL}/api/quotes/generate-pdf-with-template",
                   json=base_payload(cliente_nombre="TEST_MULTI", multirif_distribution=dist))
        assert r.status_code == 200, r.text[:300]
        pg = pages(r.content)
        p1 = norm(pg[0])
        print(p1[:2500])
        assert "ALCANCE DE LA COTIZACI" in p1
        assert "VARIOS RIF (4)" in p1
        assert "MARCA: MARCA_A" in p1 and "MARCA: MARCA_B" in p1
        assert "TEST_RAZON 3" in p1
        assert "SEDE PRINCIPAL" in p1
        assert "TEST_COT-381" in p1  # quote number card on page 1
        # page 2 must not be the cover overflow
        assert "ALCANCE DE LA COTIZACI" not in norm(pg[1])

    def test_single_rif_multi_store_scope_block(self, s):
        dist = [{"client_id": "c1", "rif": "J500000010", "client_name": "TEST_ONE", "marca_name": "M1",
                 "stores": [{"name": "Principal"}, {"name": "Suc A"}, {"name": "Suc B"}]}]
        r = s.post(f"{BASE_URL}/api/quotes/generate-pdf-with-template", json=base_payload(cliente_nombre="TEST_ONE", multirif_distribution=dist))
        assert r.status_code == 200
        p1 = norm(pages(r.content)[0])
        assert "ALCANCE DE LA COTIZACI" in p1
        assert "VARIOS RIF" not in p1

    def test_regenerate_multi_quote(self, s):
        r = s.post(f"{BASE_URL}/api/quotes/{MULTI_QID}/regenerate-pdf", json={})
        assert r.status_code == 200, r.text[:300]
        path = "/app/backend/uploads/COT-2026-11-110-PYME_Cotizacion.pdf"
        content = r.content if r.headers.get("content-type", "").startswith("application/pdf") else open(path, "rb").read()
        pg = pages(content)
        p1 = norm(pg[0])
        print(r.headers.get("content-type"), p1[:2500])
        assert "VARIOS RIF (6)" in p1
        assert "ALCANCE DE LA COTIZACI" in p1
        assert "MARCA: ADIDAS" in p1 and "MARCA: ARDENE" in p1
        assert "SEDE PRINCIPAL" in p1
        assert "COT-2026-11-110-PYME" in p1
        assert "FUTWEAR GROUP" in p1
        assert "ALCANCE DE LA COTIZACI" not in norm(pg[1])

    def test_stress_many_rifs_long_names_fit_page1(self, s):
        dist = [{"client_id": f"c{i}", "rif": f"J5000000{i}0", "client_name": f"TEST_RAZON SOCIAL MUY LARGA DE PRUEBA NUMERO {i}, C.A.",
                 "marca_name": f"MARCA_{i % 4}", "stores": [{"name": "Principal"}] + [{"name": f"Sucursal Centro Comercial {j}"} for j in range(6)]}
                for i in range(9)]
        r = s.post(f"{BASE_URL}/api/quotes/generate-pdf-with-template",
                   json=base_payload(cliente_nombre="TEST_MULTI", multirif_distribution=dist, quote_type="VPOS", template_type="vpos_pyme",
                                     integrator_name="Integrador X", pinpad_model="P630", sponsor_bank_name="Banco X", cantidad_cajas=20))
        assert r.status_code == 200, r.text[:300]
        pg = pages(r.content)
        p1, p2 = norm(pg[0]), norm(pg[1])
        print(p1[:3000]); print("P2:", p2[:400])
        assert "VARIOS RIF (9)" in p1
        assert "RIF ADICIONAL" in p1
        assert "NÚMERO DE COTIZACIÓN" in p1 and "FECHA DE VENCIMIENTO" in p1
        assert "DOCUMENTO CONFIDENCIAL • MEGA SOFT" in p1
        assert "NÚMERO DE COTIZACIÓN" not in p2
