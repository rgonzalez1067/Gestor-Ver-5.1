# Iter390: Mantenimiento del Directorio de Integradores (eliminar seguro, purge empresas vacías, certificados legacy y carga ZIP)
import io
import os
import zipfile
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
BASE = "http://localhost:8001/api"  # URL pública bloquea urllib/requests (1010) según nota del agente
PWD = "QaIntegr2026*Ok"
mdb = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
REF_ID = "int_84c3acb5fc3b"


def _login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PWD})
    assert r.status_code == 200, r.text
    tok = r.json().get("session_token") or r.json().get("token")
    assert tok, r.json()
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin():
    return _login("qa.integradores@megasoft.com.ve")


@pytest.fixture(scope="module")
def editor():
    return _login("qa.editor@megasoft.com.ve")


@pytest.fixture(scope="module")
def gerente():
    return _login("qa.gerente@megasoft.com.ve")


@pytest.fixture(scope="module")
def created():
    d = {"apps": [], "companies": [], "certs": []}
    yield d
    if d["apps"]:
        mdb.integrators.delete_many({"integrator_id": {"$in": d["apps"]}})
    if d["companies"]:
        mdb.empresas_integradoras.delete_many({"empresa_id": {"$in": d["companies"]}})
    if d["certs"]:
        mdb.integrator_certificates.delete_many({"certificate_id": {"$in": d["certs"]}})


# --- References / safe delete of apps
class TestAppDelete:
    def test_references_structure(self, admin):
        r = requests.get(f"{BASE}/integrators/{REF_ID}/references", headers=admin)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["quotes"], list) and len(d["quotes"]) > 0
        assert {"quote_number", "client_name", "status"} <= set(d["quotes"][0].keys())
        assert isinstance(d["projects"], list)
        assert isinstance(d["certificates"], int)
        print("refs:", len(d["quotes"]), len(d["projects"]), d["certificates"])

    def test_references_404(self, admin):
        r = requests.get(f"{BASE}/integrators/int_nope_xyz/references", headers=admin)
        assert r.status_code == 404

    def test_delete_forbidden_editor(self, editor):
        r = requests.delete(f"{BASE}/integrators/{REF_ID}/safe", headers=editor)
        assert r.status_code == 403, r.text
        assert "Eliminar Empresas y Aplicativos" in r.json()["detail"]

    def test_delete_referenced_409(self, admin):
        r = requests.delete(f"{BASE}/integrators/{REF_ID}/safe", headers=admin)
        assert r.status_code == 409, r.text
        det = r.json()["detail"]
        assert "message" in det and det["quotes"]
        assert mdb.integrators.find_one({"integrator_id": REF_ID}) is not None

    def test_create_and_delete_unreferenced(self, gerente, created):
        ex = mdb.integrators.find_one({"integrator_id": REF_ID}, {"_id": 0})
        payload = {"name": f"QA Duplicado {uuid.uuid4().hex[:5]}", "app_name": "QA Duplicado App",
                   "integration_type": ex.get("integration_type") or "CR", "integrator_type": "Integrador"}
        r = requests.post(f"{BASE}/integrators", json=payload, headers=gerente)
        assert r.status_code in (200, 201), r.text
        iid = r.json().get("integrator_id") or (r.json().get("integrator") or {}).get("integrator_id")
        assert iid, r.json()
        created["apps"].append(iid)
        emp = (mdb.integrators.find_one({"integrator_id": iid}) or {}).get("empresa_integradora_id")
        if emp and mdb.integrators.count_documents({"empresa_integradora_id": emp}) == 1:
            created["companies"].append(emp)
        print("created app", iid, "empresa", emp)
        ref = requests.get(f"{BASE}/integrators/{iid}/references", headers=gerente).json()
        assert ref == {"quotes": [], "projects": [], "certificates": 0}
        d = requests.delete(f"{BASE}/integrators/{iid}/safe", headers=gerente)
        assert d.status_code == 200, d.text
        assert "eliminado" in d.json()["message"]
        assert mdb.integrators.find_one({"integrator_id": iid}) is None
        assert requests.delete(f"{BASE}/integrators/{iid}/safe", headers=gerente).status_code == 404


# --- Companies safe delete / purge
class TestCompanies:
    def test_delete_company_with_apps_400(self, admin):
        emp = mdb.integrators.find_one({"integrator_id": REF_ID}).get("empresa_integradora_id")
        assert emp
        r = requests.delete(f"{BASE}/integrator-companies/{emp}/safe", headers=admin)
        assert r.status_code == 400, r.text
        assert "aplicativo" in r.json()["detail"]

    def test_delete_company_editor_403(self, editor):
        r = requests.delete(f"{BASE}/integrator-companies/emp_whatever/safe", headers=editor)
        assert r.status_code == 403
        r = requests.post(f"{BASE}/integrator-companies/purge-empty", headers=editor)
        assert r.status_code == 403

    def test_delete_empty_company_safe(self, admin, created):
        eid = f"emp_qa390{uuid.uuid4().hex[:6]}"
        mdb.empresas_integradoras.insert_one({"empresa_id": eid, "name": "QA Empresa Vacia 390", "contacts": []})
        created["companies"].append(eid)
        r = requests.delete(f"{BASE}/integrator-companies/{eid}/safe", headers=admin)
        assert r.status_code == 200, r.text
        assert mdb.empresas_integradoras.find_one({"empresa_id": eid}) is None
        assert requests.delete(f"{BASE}/integrator-companies/{eid}/safe", headers=admin).status_code == 404

    def test_purge_empty_only_if_all_empty_are_qa(self, gerente, created):
        used = set(mdb.integrators.distinct("empresa_integradora_id"))
        empty = [e for e in mdb.empresas_integradoras.find({}, {"_id": 0, "empresa_id": 1, "name": 1}) if e["empresa_id"] not in used]
        print("empty companies before:", empty)
        non_qa = [e for e in empty if not str(e.get("razon_social") or e.get("name") or "").upper().startswith(("QA", "TEST"))]
        if non_qa:
            pytest.skip(f"Hay empresas vacías reales {non_qa}: no se ejecuta purge")
        eid = f"emp_qa390{uuid.uuid4().hex[:6]}"
        mdb.empresas_integradoras.insert_one({"empresa_id": eid, "name": "QA Purge 390", "contacts": []})
        created["companies"].append(eid)
        before = mdb.empresas_integradoras.count_documents({})
        r = requests.post(f"{BASE}/integrator-companies/purge-empty", headers=gerente)
        assert r.status_code == 200, r.text
        assert r.json()["deleted"] == len(empty) + 1
        assert mdb.empresas_integradoras.count_documents({}) == before - r.json()["deleted"]


# --- Legacy rebuild
class TestRebuild:
    def test_rebuild_editor_403(self, editor):
        assert requests.post(f"{BASE}/integrators/certificates/rebuild-legacy", headers=editor).status_code == 403

    def test_rebuild_idempotent(self, gerente):
        r = requests.post(f"{BASE}/integrators/certificates/rebuild-legacy", headers=gerente)
        assert r.status_code == 200, r.text
        d = r.json()
        print(d)
        assert d["created"] == 0
        names = sorted(s["name"] for s in d["skipped"])
        print("skipped:", names, [s["reason"] for s in d["skipped"]])
        assert len(d["skipped"]) == 3
        for s in d["skipped"]:
            assert s["reason"] and "reconstruir" in s["reason"].lower() or "plantilla" in s["reason"].lower()

    def test_legacy_cert_fields_and_pdf(self, admin):
        legacy = list(mdb.integrator_certificates.find({"origin": "legacy"}, {"_id": 0, "content_b64": 0}))
        assert len(legacy) >= 33, len(legacy)
        c = legacy[0]
        intg = mdb.integrators.find_one({"integrator_id": c["integrator_id"]}, {"_id": 0})
        assert c["created_at"] == intg["certified_at"]
        assert c["status"] == "vigente"
        assert c["origin_label"].startswith("Reconstruido - certificación del ")
        lst = requests.get(f"{BASE}/integrators/{c['integrator_id']}/certificates", headers=admin).json()
        assert any(x["certificate_id"] == c["certificate_id"] for x in lst["certificates"])
        dl = requests.get(f"{BASE}/integrators/certificates/{c['certificate_id']}/download", headers=admin)
        assert dl.status_code == 200
        assert dl.content[:5] == b"%PDF-"
        bad = [x["certificate_id"] for x in legacy if x.get("status") != "vigente"]
        assert not bad, bad


# --- Bulk upload ZIP
def _zip(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n, data in files.items():
            z.writestr(n, data)
    return b.getvalue()


PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


class TestBulk:
    def test_bulk_editor_403(self, editor):
        r = requests.post(f"{BASE}/integrators/certificates/bulk-upload", headers=editor,
                          files={"file": ("c.zip", _zip({"a.pdf": PDF}), "application/zip")})
        assert r.status_code == 403

    def test_bulk_invalid_zip(self, gerente):
        r = requests.post(f"{BASE}/integrators/certificates/bulk-upload", headers=gerente,
                          files={"file": ("c.zip", b"not a zip", "application/zip")})
        assert r.status_code == 400
        assert "ZIP" in r.json()["detail"]

    def test_bulk_matching(self, gerente, created):
        uid = f"int_qa390uniq{uuid.uuid4().hex[:4]}"
        mdb.integrators.insert_one({"integrator_id": uid, "name": "QAUNIQ Soluciones C.A", "app_name": "Pago Movil V2"})
        created["apps"].append(uid)
        binaural = list(mdb.integrators.find({"name": {"$regex": "^Binaural", "$options": "i"}}, {"_id": 0, "integrator_id": 1, "name": 1, "app_name": 1}))
        print("binaural apps:", binaural)
        files = {
            "Certificado_Binaural C.A_Odoo Versión 16.pdf": PDF,
            "Certificado_ZZQQ Inexistente XYZ.pdf": PDF,
            "Certificado_QAUNIQ Soluciones C.A_Pago Movil V2.pdf": PDF,
            "notes.txt": b"hello",
            "sub/fake.pdf": b"NOTPDF",
        }
        r = requests.post(f"{BASE}/integrators/certificates/bulk-upload", headers=gerente,
                          files={"file": ("c.zip", _zip(files), "application/zip")})
        assert r.status_code == 200, r.text
        d = r.json()
        print(d)
        new = list(mdb.integrator_certificates.find({"origin_label": {"$regex": "^Carga en lote"}, "original_name": {"$in": list(files)}}, {"certificate_id": 1}))
        created["certs"].extend([c["certificate_id"] for c in new])
        um = {u["filename"]: u["reason"] for u in d["unmatched"]}
        assert "notes.txt" not in um and all(m["filename"] != "notes.txt" for m in d["matched"])
        assert um.get("fake.pdf") == "No es un PDF válido"
        assert um.get("Certificado_ZZQQ Inexistente XYZ.pdf") == "Sin coincidencia"
        created["certs"].extend([c["certificate_id"] for c in mdb.integrator_certificates.find({"integrator_id": uid}, {"certificate_id": 1})])
        m = [x for x in d["matched"] if x["filename"].startswith("Certificado_QAUNIQ")]
        assert len(m) == 1 and m[0]["integrator_id"] == uid, d
        c = mdb.integrator_certificates.find_one({"integrator_id": uid}, {"_id": 0, "content_b64": 0})
        assert c["origin"] == "manual" and c["origin_label"].startswith("Carga en lote")
        # Binaural C.A / Odoo Versión 16 exists twice (exact duplicates int_f6cbdce034f9 & int_66e555d93dd7) -> ambiguous
        print("Binaural result:", um.get("Certificado_Binaural C.A_Odoo Versión 16.pdf"))

    def test_bulk_ambiguous(self, gerente, created):
        # Two QA twins with same company name -> ambiguous
        ids = []
        for i in range(2):
            iid = f"int_qa390amb{i}{uuid.uuid4().hex[:4]}"
            mdb.integrators.insert_one({"integrator_id": iid, "name": "QAZZAMBIG Corp", "app_name": f"Tool{i}"})
            ids.append(iid)
            created["apps"].append(iid)
        r = requests.post(f"{BASE}/integrators/certificates/bulk-upload", headers=gerente,
                          files={"file": ("c.zip", _zip({"Certificado_QAZZAMBIG Corp.pdf": PDF}), "application/zip")})
        assert r.status_code == 200
        d = r.json()
        print(d)
        created["certs"].extend([c["certificate_id"] for c in mdb.integrator_certificates.find({"integrator_id": {"$in": ids}}, {"certificate_id": 1})])
        assert d["unmatched"] and d["unmatched"][0]["reason"].startswith("Ambiguo")
