# Iter405: Ampliación de tipo vigente — Matriz de Productos S/R (expand, productos_a_certificar, emisión incremental)
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"}
IMPL_WITH_TPL = "user_c7d5edd6b6ea"  # Katherine Sanoja (tiene plantilla de certificado)

P_TDD, P_C2P, P_BIO, P_P2C, P_ZELLE = "prod_tdd_tdc", "prod_c2p", "prod_biopago", "prod_verificacion_p2c", "prod_verificacion_pago_zelle"

STATE = {}


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    tok = r.json().get("session_token") or r.json().get("token")
    ses.headers.update({"Authorization": f"Bearer {tok}"})
    return ses


@pytest.fixture(scope="module", autouse=True)
def cleanup(s):
    yield
    mc = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    iid = STATE.get("iid")
    if iid:
        doc = mc.integrators.find_one({"integrator_id": iid}, {"_id": 0, "empresa_integradora_id": 1})
        mc.integrator_certificates.delete_many({"integrator_id": iid})
        r = s.delete(f"{BASE_URL}/api/integrators/{iid}")
        print("cleanup integrator", r.status_code)
        emp = (doc or {}).get("empresa_integradora_id")
        if emp and not mc.integrators.count_documents({"empresa_integradora_id": emp}):
            mc.empresas_integradoras.delete_one({"empresa_id": emp, "razon_social": {"$regex": "^TEST_"}})


def _put(s, certs, **extra):
    cur = s.get(f"{BASE_URL}/api/integrators/{STATE['iid']}").json()
    body = {k: cur.get(k) for k in ("name", "integrator_type", "integration_type", "app_name", "integration_modality",
                                    "implementador", "implementador_user_id", "contacts")}
    body["integrator_status"] = cur.get("integrator_status") if cur.get("integrator_status") in ("Certificado", "En proceso", "Suspendido") else "En proceso"
    body["certifications"] = certs
    body.update(extra)
    return s.put(f"{BASE_URL}/api/integrators/{STATE['iid']}", json=body)


def _get(s):
    return s.get(f"{BASE_URL}/api/integrators/{STATE['iid']}").json()


def _reissue(s):
    return s.post(f"{BASE_URL}/api/integrators/{STATE['iid']}/certificates/reissue",
                  data={"componente": "TEST_Comp", "version_componente": "1.0"})


class TestExpansionMatrix:
    def test_01_create_and_baseline(self, s):
        name = f"TEST_ExpSR_{uuid.uuid4().hex[:6]}"
        r = s.post(f"{BASE_URL}/api/integrators", json={
            "name": name, "integrator_type": "Integrador", "integration_type": "CR", "app_name": "TEST_App",
            "integration_modality": "Rest", "contacts": [{"name": "TEST Resp", "email": "test_resp@example.com"}]})
        assert r.status_code == 200, r.text
        STATE["iid"] = r.json()["integrator_id"]
        STATE["name"] = r.json()["name"]
        products = s.get(f"{BASE_URL}/api/integrators/products").json()
        certs = {p["service_id"]: "N/A" for p in products}
        certs.update({P_TDD: "C", P_C2P: "C", P_P2C: "P"})
        r = _put(s, certs, implementador="Katherine Sanoja", implementador_user_id=IMPL_WITH_TPL)
        assert r.status_code == 200, r.text
        # Primer certificado (línea base) -> TDD + C2P
        r = _reissue(s)
        assert r.status_code == 200, r.text
        d = _get(s)
        assert set(d.get("cert_baseline") or []) == {P_TDD, P_C2P}

    def test_02_expand_rules(self, s):
        r = s.post(f"{BASE_URL}/api/integrators/{STATE['iid']}/expand", json={
            "solicitados": {P_BIO: "S", P_TDD: "R", P_C2P: "S", P_P2C: "R"}})
        assert r.status_code == 200, r.text
        d = r.json()
        c = d["certifications"]
        assert d["project_scope"] == "expansion"
        assert c[P_BIO] == "S"
        assert c[P_TDD] == "R"
        assert c[P_C2P] == "C", "S must be ignored on C product"
        assert c[P_P2C] == "P", "R must be ignored on non-C product"
        assert d["productos_certificar"] == "TDD/TDC (Recertificación - R), Biopago (Nuevo - S)", d["productos_certificar"]
        assert "correo_eventual" not in d or not d.get("correo_eventual")
        # baseline untouched by expand
        assert set(d.get("cert_baseline") or []) == {P_TDD, P_C2P}

    def test_03_template_variable(self, s):
        r = s.post(f"{BASE_URL}/api/integrators/{STATE['iid']}/preview-email",
                   json={"subject": "X {{productos_a_certificar}}", "message": "M: {{productos_a_certificar}} | {{Productos_Certificar_Integrador}}"})
        assert r.status_code == 200, r.text
        msg = r.json()["message"]
        print("preview:", msg)
        assert "TDD/TDC (Recertificación - R)<br>Biopago (Nuevo - S)" in msg

    def test_04_emit_incremental(self, s):
        r = _reissue(s)
        assert r.status_code == 200, r.text
        certs = s.get(f"{BASE_URL}/api/integrators/{STATE['iid']}/certificates").json()["certificates"]
        latest = certs[0]
        assert latest["products_included_ids"] == [P_TDD, P_BIO], latest.get("products_included_ids")
        assert latest["status"] == "vigente"
        d = _get(s)
        assert d["certifications"][P_TDD] == "C" and d["certifications"][P_BIO] == "C"
        assert set(d["cert_baseline"]) >= {P_TDD, P_C2P, P_BIO}
        assert "R" not in d["certifications"].values() and "S" not in d["certifications"].values()

    def test_05_expand_with_none(self, s):
        before = _get(s)["certifications"]
        r = s.post(f"{BASE_URL}/api/integrators/{STATE['iid']}/expand", json={"solicitados": {}})
        assert r.status_code == 200, r.text
        assert r.json()["certifications"] == before
        assert r.json()["productos_certificar"] == ""

    def test_06_matrix_put_R_then_revert_to_C_not_new(self, s):
        """Implementer marks C2P as R (saved), then reverts R->C (saved). C2P must NOT be treated as a new certification."""
        d = _get(s)
        certs = dict(d["certifications"]); certs[P_C2P] = "R"
        assert _put(s, certs).status_code == 200
        certs[P_C2P] = "C"
        assert _put(s, certs).status_code == 200
        d = _get(s)
        print("baseline after revert:", d.get("cert_baseline"))
        assert P_C2P in (d.get("cert_baseline") or []), "C2P dropped from baseline after R->C revert -> will be re-certified as new"

    def test_07_matrix_put_S_persist(self, s):
        d = _get(s)
        certs = dict(d["certifications"]); certs[P_ZELLE] = "S"; certs[P_TDD] = "R"
        r = _put(s, certs)
        assert r.status_code == 200, r.text
        d = _get(s)
        assert d["certifications"][P_ZELLE] == "S" and d["certifications"][P_TDD] == "R"
