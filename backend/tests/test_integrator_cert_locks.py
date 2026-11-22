# Iter387: Bloqueo de aplicativos certificados (Función Especial + motivo), certificados desactualizados, re-emisión e histórico.
# Requiere fixture: python /app/backend/tests/ui_fixture_iter387_locks.py create (copias TEST_ de int_f6cbdce034f9)
import io
import pytest
import requests

BASE = "http://localhost:8001/api"  # URL pública bloqueada por Cloudflare (1010) para clientes python
PWD = "QaIntegr2026*Ok"
LOCK, ACTV, NOTPL, CLOSED = "int_test387lock", "int_test387actv", "int_test387notp", "int_test387clos"
KEYS = ['name', 'integrator_type', 'integration_type', 'app_name', 'integration_modality', 'integrator_status', 'gestor',
        'categoria', 'ticket_number', 'certifications', 'last_contact_date', 'contacts', 'integration_phase', 'coordinador',
        'coordinador_user_id', 'implementador', 'implementador_user_id', 'project_start_date', 'project_name', 'observations',
        'comercios_relacionados', 'componente_version', 'productos_certificar', 'correo_eventual', 'project_scope',
        'principal_contact_name', 'principal_contact_phone', 'principal_contact_email', 'interface_negotiation',
        'test_env_start_date', 'test_env_end_date', 'empresa_integradora_id']
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PWD})
    assert r.status_code == 200, r.text
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    return s


@pytest.fixture(scope="module")
def admin():
    return login("qa.integradores@megasoft.com.ve")


@pytest.fixture(scope="module")
def editor():
    return login("qa.editor@megasoft.com.ve")


@pytest.fixture(scope="module")
def gerente():
    return login("qa.gerente@megasoft.com.ve")


def payload(s, iid, **patch):
    i = s.get(f"{BASE}/integrators/{iid}").json()
    out = {k: i[k] for k in KEYS if i.get(k) is not None}
    if out.get("integrator_status") == "Cerrado":
        out.pop("integrator_status")
    out.update(patch)
    return out


def matrix(s, iid, pid, val):
    p = payload(s, iid)
    p["certifications"] = {**p["certifications"], pid: val}
    return p


class TestLock:
    def test_editor_matrix_403(self, editor):
        r = editor.put(f"{BASE}/integrators/{LOCK}", json=matrix(editor, LOCK, "prod_biopago", "C"))
        assert r.status_code == 403, r.text
        assert "Modificar Aplicativos Certificados" in r.json()["detail"]

    def test_editor_data_403(self, editor):
        r = editor.put(f"{BASE}/integrators/{LOCK}", json=payload(editor, LOCK, observations="TEST_obs editor"))
        assert r.status_code == 403

    def test_editor_closed_403(self, editor):
        r = editor.put(f"{BASE}/integrators/{CLOSED}", json=payload(editor, CLOSED, observations="TEST_obs closed"))
        assert r.status_code == 403

    def test_editor_noop_200(self, editor):
        r = editor.put(f"{BASE}/integrators/{LOCK}", json=payload(editor, LOCK))
        assert r.status_code == 200, r.text

    def test_gerente_no_reason_400(self, gerente):
        r = gerente.put(f"{BASE}/integrators/{LOCK}", json=matrix(gerente, LOCK, "prod_biopago", "C"))
        assert r.status_code == 400
        r = gerente.put(f"{BASE}/integrators/{LOCK}", json={**matrix(gerente, LOCK, "prod_biopago", "C"), "change_reason": "corto"})
        assert r.status_code == 400

    def test_gerente_with_reason_200_and_bitacora(self, gerente):
        r = gerente.put(f"{BASE}/integrators/{LOCK}", json={**matrix(gerente, LOCK, "prod_biopago", "C"), "change_reason": "TEST_ QA ajuste de matriz"})
        assert r.status_code == 200, r.text
        assert r.json()["certifications"]["prod_biopago"] == "C"
        b = gerente.get(f"{BASE}/integrators/{LOCK}/bitacora").json()
        entries = b if isinstance(b, list) else b.get("entries", b.get("items", []))
        txt = " ".join(e.get("description", "") for e in entries)
        assert "Motivo: TEST_ QA ajuste de matriz" in txt
        assert "Matriz · " in txt and "N/A → C" in txt
        assert gerente.get(f"{BASE}/integrators/{LOCK}").json().get("cert_outdated") in (None, False)  # sin certificados

    def test_admin_with_reason(self, admin):
        r = admin.put(f"{BASE}/integrators/{LOCK}", json=payload(admin, LOCK, observations="TEST_ obs admin"))
        assert r.status_code == 400
        r = admin.put(f"{BASE}/integrators/{LOCK}", json=payload(admin, LOCK, observations="TEST_ obs admin", change_reason="TEST_ motivo admin QA"))
        assert r.status_code == 200
        assert r.json()["observations"] == "TEST_ obs admin"

    def test_active_regression_editor(self, editor):
        r = editor.put(f"{BASE}/integrators/{ACTV}", json=matrix(editor, ACTV, "prod_biopago", "C"))
        assert r.status_code == 200, r.text
        r = editor.put(f"{BASE}/integrators/{ACTV}", json=payload(editor, ACTV, observations="TEST_ activo"))
        assert r.status_code == 200 and r.json()["observations"] == "TEST_ activo"

    def test_partial_payload_bypass(self, editor):
        """Payload parcial (sin certifications) NO debe borrar la matriz de un aplicativo bloqueado."""
        before = editor.get(f"{BASE}/integrators/{LOCK}").json()["certifications"]
        p = {"name": "x", "integrator_type": "Integrador", "app_name": "TEST_QA387 locked", "integrator_status": "Certificado"}
        r = editor.put(f"{BASE}/integrators/{LOCK}", json=p)
        after = editor.get(f"{BASE}/integrators/{LOCK}").json()
        assert after.get("certifications") == before, f"status={r.status_code} matriz borrada: {after.get('certifications')}"


class TestCertificates:
    def test_upload_then_outdated(self, admin, gerente):
        r = admin.post(f"{BASE}/integrators/{LOCK}/certificates", files={"file": ("TEST_cert.pdf", io.BytesIO(PDF), "application/pdf")})
        assert r.status_code == 200, r.text
        r = gerente.put(f"{BASE}/integrators/{LOCK}", json={**matrix(gerente, LOCK, "prod_cashea", "C"), "change_reason": "TEST_ QA cambio cashea"})
        assert r.status_code == 200
        assert gerente.get(f"{BASE}/integrators/{LOCK}").json()["cert_outdated"] is True
        certs = gerente.get(f"{BASE}/integrators/{LOCK}/certificates").json()["certificates"]
        assert certs and all(c["status"] == "desactualizado" for c in certs)

    def test_reissue_editor_403(self, editor):
        r = editor.post(f"{BASE}/integrators/{LOCK}/certificates/reissue", data={"componente": "Odoo", "version_componente": "16"})
        assert r.status_code == 403

    def test_reissue_gerente_ok(self, gerente):
        r = gerente.post(f"{BASE}/integrators/{LOCK}/certificates/reissue", data={"componente": "TEST_Odoo", "version_componente": "16"})
        assert r.status_code == 200, r.text
        new_id = r.json()["certificate_id"]
        certs = gerente.get(f"{BASE}/integrators/{LOCK}/certificates").json()["certificates"]
        st = {c["certificate_id"]: c["status"] for c in certs}
        assert st[new_id] == "vigente"
        assert all(v == "reemplazado" for k, v in st.items() if k != new_id)
        i = gerente.get(f"{BASE}/integrators/{LOCK}").json()
        assert i["cert_outdated"] is False
        d = gerente.get(f"{BASE}/integrators/certificates/{new_id}/download")
        assert d.status_code == 200 and d.content[:5] == b"%PDF-"

    def test_reissue_missing_fields_400(self, gerente):
        r = gerente.post(f"{BASE}/integrators/{NOTPL}/certificates/reissue", data={})
        assert r.status_code == 400

    def test_reissue_no_template_400(self, gerente):
        r = gerente.post(f"{BASE}/integrators/{NOTPL}/certificates/reissue", data={"componente": "X", "version_componente": "1"})
        assert r.status_code == 400 and "plantilla" in r.json()["detail"]

    def test_set_status(self, gerente, editor):
        certs = gerente.get(f"{BASE}/integrators/{LOCK}/certificates").json()["certificates"]
        old = [c for c in certs if c["status"] == "reemplazado"][0]["certificate_id"]
        assert editor.patch(f"{BASE}/integrators/certificates/{old}/status", json={"status": "vigente"}).status_code == 403
        assert gerente.patch(f"{BASE}/integrators/certificates/{old}/status", json={"status": "bogus"}).status_code == 422
        assert gerente.patch(f"{BASE}/integrators/certificates/{old}/status", json={"status": "vigente"}).status_code == 200
        st = {c["certificate_id"]: c["status"] for c in gerente.get(f"{BASE}/integrators/{LOCK}/certificates").json()["certificates"]}
        assert st[old] == "vigente" and all(v != "vigente" for k, v in st.items() if k != old)
        assert gerente.patch(f"{BASE}/integrators/certificates/{old}/status", json={"status": "anulado"}).status_code == 200
        st = {c["certificate_id"]: c["status"] for c in gerente.get(f"{BASE}/integrators/{LOCK}/certificates").json()["certificates"]}
        assert st[old] == "anulado"
        assert gerente.patch(f"{BASE}/integrators/certificates/cert_nope/status", json={"status": "anulado"}).status_code == 404


class TestCatalog:
    def test_catalog_has_flags(self, admin):
        r = admin.get(f"{BASE}/admin/permission-catalog")
        assert r.status_code == 200
        txt = r.text
        assert "integradores:editar_certificados" in txt and "Modificar Aplicativos Certificados" in txt
        assert "integradores:gestionar_certificados" in txt and "Gestionar Certificados (Gerente de Implementación)" in txt
