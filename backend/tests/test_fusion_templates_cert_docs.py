# Plantillas de Fusión (email_templates tipo_plantilla) + Documentos de la Certificación por Aplicativo
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
EMAIL = "qa.integradores@megasoft.com.ve"
PASSWORD = "QaIntegr2026*Ok"
CREATED = []


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    d = r.json()
    tok = d.get("session_token") or d.get("token")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    yield s
    for tid in CREATED:
        s.delete(f"{BASE_URL}/api/email-templates/{tid}")


def _tid(p):
    return f"TEST_{p}_{int(time.time()*1000)}"


# --- Fusion templates
class TestFusion:
    def test_create_fusion_without_subject(self, client):
        tid = _tid("fus")
        r = client.post(f"{BASE_URL}/api/email-templates", json={
            "template_id": tid, "name": "TEST_Acta API", "body_html": "<p>{{empresa_integradora}}</p>",
            "tipo_plantilla": "FUSION", "context": "INTEGRADORES", "subject": "should be dropped"})
        assert r.status_code == 200, r.text
        CREATED.append(tid)
        lst = client.get(f"{BASE_URL}/api/email-templates?context=INTEGRADORES").json()
        t = next(x for x in lst if x["template_id"] == tid)
        assert t["tipo_plantilla"] == "FUSION"
        assert t.get("subject") in (None, "")

    def test_fusion_empty_body_400(self, client):
        r = client.post(f"{BASE_URL}/api/email-templates", json={
            "template_id": _tid("fusb"), "name": "TEST_x", "body_html": "<p>&nbsp; </p>",
            "tipo_plantilla": "FUSION", "context": "INTEGRADORES"})
        assert r.status_code == 400

    def test_fusion_empty_title_400(self, client):
        r = client.post(f"{BASE_URL}/api/email-templates", json={
            "template_id": _tid("fust"), "name": "  ", "body_html": "<p>a</p>",
            "tipo_plantilla": "FUSION", "context": "INTEGRADORES"})
        assert r.status_code == 400

    def test_invalid_tipo_400(self, client):
        r = client.post(f"{BASE_URL}/api/email-templates", json={
            "template_id": _tid("bad"), "name": "TEST_x", "body_html": "<p>a</p>",
            "tipo_plantilla": "OTRO", "context": "INTEGRADORES"})
        assert r.status_code == 400

    def test_comm_without_subject_400(self, client):
        r = client.post(f"{BASE_URL}/api/email-templates", json={
            "template_id": _tid("com"), "name": "TEST_c", "body_html": "<p>a</p>",
            "tipo_plantilla": "COMUNICACION", "context": "INTEGRADORES", "subject": " "})
        assert r.status_code == 400
        assert "asunto" in r.json()["detail"].lower()

    def test_comm_with_subject_and_update_fusion(self, client):
        tid = _tid("com2")
        r = client.post(f"{BASE_URL}/api/email-templates", json={
            "template_id": tid, "name": "TEST_Comm API", "subject": "Hola {{rif}}", "body_html": "<p>a</p>",
            "context": "INTEGRADORES"})
        assert r.status_code == 200, r.text
        CREATED.append(tid)
        t = next(x for x in client.get(f"{BASE_URL}/api/email-templates?context=INTEGRADORES").json() if x["template_id"] == tid)
        assert t["tipo_plantilla"] == "COMUNICACION"
        # update to fusion via PUT -> subject removed
        r = client.put(f"{BASE_URL}/api/email-templates/{tid}", json={
            "template_id": tid, "name": "TEST_Comm API", "subject": "x", "body_html": "<p>b</p>",
            "tipo_plantilla": "FUSION", "context": "INTEGRADORES"})
        assert r.status_code == 200
        t = next(x for x in client.get(f"{BASE_URL}/api/email-templates?context=INTEGRADORES").json() if x["template_id"] == tid)
        assert t["tipo_plantilla"] == "FUSION" and not t.get("subject")

    def test_other_context_without_subject_ok(self, client):
        tid = _tid("np")
        r = client.post(f"{BASE_URL}/api/email-templates", json={
            "template_id": tid, "name": "TEST_np", "body_html": "<p>a</p>", "context": "NUEVOS_PRODUCTOS"})
        assert r.status_code == 200, r.text
        CREATED.append(tid)

    def test_audit_trail_recorded(self, client):
        time.sleep(1)
        r = client.get(f"{BASE_URL}/api/audit-trails", params={"registro": "TEST_Acta API", "page_size": 50})
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert any(i.get("accion", i.get("action")) in ("CREATE", "CREAR") or "CREATE" in str(i) for i in items), items[:2]


# --- Cert docs
class TestCertDocs:
    def test_cert_docs(self, client):
        lst = client.get(f"{BASE_URL}/api/integrators").json()
        items = lst if isinstance(lst, list) else lst.get("items") or lst.get("integrators") or []
        assert items
        app = items[0]
        r = client.get(f"{BASE_URL}/api/integrators/{app['integrator_id']}/certification-documents")
        assert r.status_code == 200, r.text
        d = r.json()
        emp = app.get("empresa_integradora_id") or "sin_empresa"
        assert d["folder"]["path"] == f"/storage/integradores/{emp}/aplicativos/{app['integrator_id']}/documentos_certificacion/"
        assert d["documents"] == []

    def test_cert_docs_404(self, client):
        r = client.get(f"{BASE_URL}/api/integrators/nope_xyz/certification-documents")
        assert r.status_code == 404

    def test_cert_docs_unauth(self):
        r = requests.get(f"{BASE_URL}/api/integrators/nope_xyz/certification-documents")
        assert r.status_code in (401, 403)

    def test_preview_new_vars(self, client):
        lst = client.get(f"{BASE_URL}/api/integrators").json()
        items = lst if isinstance(lst, list) else lst.get("items") or lst.get("integrators") or []
        app = items[0]
        r = client.post(f"{BASE_URL}/api/integrators/{app['integrator_id']}/preview-email",
                        json={"subject": "s", "message": "{{fecha_actual}}|{{nombre_aplicativo}}|{{empresa_integradora}}"})
        assert r.status_code == 200
        msg = r.json()["message"]
        assert "{{" not in msg
        assert msg.split("|")[0].count("/") == 2
