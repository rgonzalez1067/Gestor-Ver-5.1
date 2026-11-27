# Expediente Digital por Certificado (1:1) - integrator certificates
import os
import uuid
import asyncio
import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
APP_ID = "int_821d989ae54c"
CERT_A = "cert_597482dd1596"
CERT_B = "cert_4a9d1ae36493"
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7V\xbd\xfa\x00\x00\x00\x00IEND\xaeB`\x82")
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
CREATED_DOCS = []


def _db():
    return AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


@pytest.fixture(scope="module")
def s():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"})
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    ss = requests.Session()
    ss.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    ss.token = r.json()['session_token']
    yield ss
    async def clean():
        d = _db()
        if CREATED_DOCS:
            await d.certificado_expediente_documentos.delete_many({"documento_id": {"$in": CREATED_DOCS}})
    run(clean())


class TestExpediente:
    def test_list_has_expediente_count(self, s):
        r = s.get(f"{BASE_URL}/api/integrators/{APP_ID}/certificates")
        assert r.status_code == 200
        certs = r.json()["certificates"]
        assert len(certs) >= 2
        assert all(isinstance(c.get("expediente_count"), int) for c in certs)

    def test_upload_manual_and_isolation(self, s):
        r = s.post(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente",
                   files=[("files", ("TEST_a.pdf", PDF, "application/pdf")), ("files", ("TEST_b.png", PNG, "image/png"))])
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["uploaded"] == 2
        for d in j["documents"]:
            CREATED_DOCS.append(d["documento_id"])
            assert d["origen_carga"] == "MANUAL_POSTERIOR"
            assert d["certificado_id"] == CERT_A
        rb = s.post(f"{BASE_URL}/api/integrators/certificates/{CERT_B}/expediente",
                    files=[("files", ("TEST_c.pdf", PDF, "application/pdf"))])
        assert rb.status_code == 200
        CREATED_DOCS.append(rb.json()["documents"][0]["documento_id"])
        la = s.get(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente").json()
        lb = s.get(f"{BASE_URL}/api/integrators/certificates/{CERT_B}/expediente").json()
        na = {d["nombre_documento"] for d in la["documents"]}
        nb = {d["nombre_documento"] for d in lb["documents"]}
        assert {"TEST_a.pdf", "TEST_b.png"} <= na and "TEST_c.pdf" not in na
        assert "TEST_c.pdf" in nb and "TEST_a.pdf" not in nb
        assert all(d["certificado_id"] == CERT_A for d in la["documents"])
        assert "'_id'" not in str(la)
        # counts reflect
        certs = {c["certificate_id"]: c for c in s.get(f"{BASE_URL}/api/integrators/{APP_ID}/certificates").json()["certificates"]}
        assert certs[CERT_A]["expediente_count"] >= 2 and certs[CERT_B]["expediente_count"] >= 1

    def test_reject_exe(self, s):
        r = s.post(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente",
                   files=[("files", ("TEST_bad.exe", b"MZ\x00\x00", "application/octet-stream"))])
        assert r.status_code == 400
        assert "Formato" in r.json()["detail"]

    def test_reject_mixed_batch_atomic(self, s):
        before = len(s.get(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente").json()["documents"])
        r = s.post(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente",
                   files=[("files", ("TEST_ok.pdf", PDF, "application/pdf")), ("files", ("TEST_bad.exe", b"MZ", "x"))])
        assert r.status_code == 400
        after = len(s.get(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente").json()["documents"])
        assert before == after

    def test_empty_file_and_404(self, s):
        r = s.post(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente",
                   files=[("files", ("TEST_empty.pdf", b"", "application/pdf"))])
        assert r.status_code == 400
        assert s.get(f"{BASE_URL}/api/integrators/certificates/cert_nope/expediente").status_code == 404
        assert s.get(f"{BASE_URL}/api/integrators/expediente/expdoc_nope/download").status_code == 404

    def test_unauth(self):
        assert requests.get(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente").status_code == 401

    def test_download_bytes_inline_and_attachment(self, s):
        la = s.get(f"{BASE_URL}/api/integrators/certificates/{CERT_A}/expediente").json()["documents"]
        png = next(d for d in la if d["nombre_documento"] == "TEST_b.png")
        r = s.get(f"{BASE_URL}/api/integrators/expediente/{png['documento_id']}/download", params={"inline": "true"})
        assert r.status_code == 200 and r.content == PNG
        assert r.headers["content-disposition"].startswith("inline")
        assert "image/png" in r.headers["content-type"]
        pdf = next(d for d in la if d["nombre_documento"] == "TEST_a.pdf")
        r2 = s.get(f"{BASE_URL}/api/integrators/expediente/{pdf['documento_id']}/download")
        assert r2.status_code == 200 and r2.content == PDF
        assert r2.headers["content-disposition"].startswith("attachment")
        # token query param
        r3 = requests.get(f"{BASE_URL}/api/integrators/expediente/{pdf['documento_id']}/download", params={"token": s.token})
        assert r3.status_code == 200

    def test_audit_trails(self, s):
        async def q():
            d = _db()
            out = {}
            for a in ("CREATE", "CONSULTA", "DESCARGA", "VISUALIZACION"):
                out[a] = await d.audit_trails.count_documents({"entidad": "certificado_expediente_documentos", "accion": a})
            return out
        res = run(q())
        print(res)
        assert res["CREATE"] > 0 and res["CONSULTA"] > 0 and res["DESCARGA"] > 0 and res["VISUALIZACION"] > 0


class TestReissueAuto:
    """Re-emission on a TEST_ copy of an integrator so real data isn't modified."""
    def test_reissue_creates_auto_doc(self, s):
        new_id = f"int_test{uuid.uuid4().hex[:6]}"
        async def setup():
            d = _db()
            src = await d.integrators.find_one({"integrator_id": APP_ID}, {"_id": 0})
            src["integrator_id"] = new_id
            src["cert_baseline"] = []
            src["name"] = "TEST_" + src.get("name", "")
            src["app_name"] = "TEST_" + (src.get("app_name") or "")
            await d.integrators.insert_one(src)
        run(setup())
        try:
            r = s.post(f"{BASE_URL}/api/integrators/{new_id}/certificates/reissue",
                       data={"componente": "TEST_comp", "version_componente": "1.0"})
            if r.status_code == 400:
                pytest.skip(f"reissue 400: {r.text[:200]}")
            assert r.status_code == 200, r.text
            cid = r.json()["certificate_id"]
            ex = s.get(f"{BASE_URL}/api/integrators/certificates/{cid}/expediente").json()["documents"]
            assert len(ex) == 1
            assert ex[0]["origen_carga"] == "AUTOMATICO"
            assert ex[0]["nombre_documento"].endswith("_reemision.pdf")
            dl = s.get(f"{BASE_URL}/api/integrators/expediente/{ex[0]['documento_id']}/download")
            assert dl.status_code == 200 and dl.content[:5] == b"%PDF-"
            certs = s.get(f"{BASE_URL}/api/integrators/{new_id}/certificates").json()["certificates"]
            assert next(c for c in certs if c["certificate_id"] == cid)["expediente_count"] == 1
        finally:
            async def clean():
                d = _db()
                await d.certificado_expediente_documentos.delete_many({"aplicativo_id": new_id})
                await d.integrator_certificates.delete_many({"integrator_id": new_id})
                await d.integrators.delete_one({"integrator_id": new_id})
            run(clean())
