# Iter397: Catálogo Productos para Integración + Certificado incremental (Delta) + inline viewer
import os
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"}
IMPL_USER = "user_c7d5edd6b6ea"
STATE = {}


def _mongo():
    env = {}
    for line in open("/app/backend/.env"):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v.strip('"')
    return MongoClient(env["MONGO_URL"])[env["DB_NAME"]]


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    assert r.status_code == 200, r.text
    tok = r.json().get("session_token") or r.json().get("token")
    ses.headers.update({"Authorization": f"Bearer {tok}"})
    return ses


@pytest.fixture(scope="module", autouse=True)
def cleanup(s):
    yield
    if os.environ.get("KEEP_TEST_DATA"):
        import json
        json.dump(STATE, open("/tmp/iter397_state.json", "w"))
        return
    db = _mongo()
    if STATE.get("app_id"):
        db.integrator_certificates.delete_many({"integrator_id": STATE["app_id"], "certificate_id": {"$in": STATE.get("certs", [])}})
        r = s.delete(f"{BASE_URL}/api/integrators/{STATE['app_id']}/safe")
        print("cleanup app", r.status_code, r.text[:200])
    for pid in STATE.get("prods", []):
        r = s.delete(f"{BASE_URL}/api/productos-integracion/{pid}")
        print("cleanup prod", pid, r.status_code)


def _products(s):
    r = s.get(f"{BASE_URL}/api/integrators/products")
    assert r.status_code == 200
    return {p["service_id"]: p["name"] for p in r.json()}


# ---- Catálogo CRUD ----
class TestCatalog:
    def test_list(self, s):
        r = s.get(f"{BASE_URL}/api/productos-integracion")
        assert r.status_code == 200
        d = r.json()
        assert len(d) >= 21
        assert all("_id" not in x and "aplicativos" in x for x in d)

    def test_create_and_matrix(self, s):
        r = s.post(f"{BASE_URL}/api/productos-integracion", json={"codigo": "test_biobdv", "nombre": "TEST_BiopagoBDV", "descripcion": "qa", "orden_despliegue": 5})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["codigo"] == "TEST_BIOBDV" and d["activo"] is True
        STATE.setdefault("prods", []).append(d["producto_id"])
        STATE["pA"] = d["producto_id"]
        prods = _products(s)
        assert prods.get(d["producto_id"]) == "TEST_BiopagoBDV"

    def test_duplicates_409(self, s):
        r1 = s.post(f"{BASE_URL}/api/productos-integracion", json={"codigo": "TEST_BIOBDV", "nombre": "TEST_Otro"})
        r2 = s.post(f"{BASE_URL}/api/productos-integracion", json={"codigo": "TEST_OTRO", "nombre": "test_biopagobdv"})
        assert r1.status_code == 409 and "código" in r1.json()["detail"]
        assert r2.status_code == 409 and "nombre" in r2.json()["detail"]

    def test_create_b_c_and_rename(self, s):
        for code, name in [("TEST_PB", "TEST_ProdB"), ("TEST_PC", "TEST_ProdC")]:
            r = s.post(f"{BASE_URL}/api/productos-integracion", json={"codigo": code, "nombre": name, "orden_despliegue": 6})
            assert r.status_code == 200, r.text
            STATE["prods"].append(r.json()["producto_id"])
        STATE["pB"], STATE["pC"] = STATE["prods"][1], STATE["prods"][2]
        r = s.put(f"{BASE_URL}/api/productos-integracion/{STATE['pB']}", json={"nombre": "TEST_ProdB_Ren"})
        assert r.status_code == 200 and r.json()["nombre"] == "TEST_ProdB_Ren"
        assert _products(s)[STATE["pB"]] == "TEST_ProdB_Ren"
        # rename to existing -> 409
        r = s.put(f"{BASE_URL}/api/productos-integracion/{STATE['pB']}", json={"nombre": "TEST_ProdC"})
        assert r.status_code == 409

    def test_inactivate_hides(self, s):
        r = s.post(f"{BASE_URL}/api/productos-integracion", json={"codigo": "TEST_INACT", "nombre": "TEST_Inactivo"})
        pid = r.json()["producto_id"]
        STATE["prods"].append(pid)
        r = s.put(f"{BASE_URL}/api/productos-integracion/{pid}", json={"activo": False})
        assert r.status_code == 200 and r.json()["activo"] is False
        assert pid not in _products(s)
        r = s.put(f"{BASE_URL}/api/productos-integracion/{pid}", json={"activo": True})
        assert pid in _products(s)

    def test_audit(self, s):
        r = s.get(f"{BASE_URL}/api/audit-trails", params={"modules": "Productos para Integración", "registro": STATE["pB"]})
        assert r.status_code == 200, r.text
        acts = {i["accion"] for i in r.json()["items"]}
        print("audit actions", acts, r.json()["total"])
        assert "CREATE" in acts and "UPDATE" in acts

    def test_delete_and_404(self, s):
        pid = STATE["prods"].pop()  # TEST_Inactivo
        r = s.delete(f"{BASE_URL}/api/productos-integracion/{pid}")
        assert r.status_code == 200
        assert pid not in _products(s)
        assert s.delete(f"{BASE_URL}/api/productos-integracion/{pid}").status_code == 404
        r = s.get(f"{BASE_URL}/api/audit-trails", params={"modules": "Productos para Integración", "registro": pid, "action": "DELETE"})
        assert r.json()["total"] >= 1

    def test_validation(self, s):
        r = s.post(f"{BASE_URL}/api/productos-integracion", json={"codigo": "X" * 31, "nombre": "TEST_x"})
        assert r.status_code == 422
        r = s.post(f"{BASE_URL}/api/productos-integracion", json={"codigo": "TEST_Y", "nombre": ""})
        assert r.status_code == 422


# ---- Delta ----
class TestDelta:
    def _certs(self, s):
        r = s.get(f"{BASE_URL}/api/integrators/{STATE['app_id']}/certificates")
        assert r.status_code == 200
        return r.json()["certificates"]

    def _put(self, s, certs):
        app = s.get(f"{BASE_URL}/api/integrators/{STATE['app_id']}").json()
        payload = {k: app.get(k) for k in ("name", "integrator_type", "app_name", "integrator_status", "empresa_integradora_id")}
        payload["certifications"] = certs
        payload["change_reason"] = "TEST_ cambio de matriz QA delta"
        r = s.put(f"{BASE_URL}/api/integrators/{STATE['app_id']}", json=payload)
        assert r.status_code == 200, r.text
        return r.json()

    def _reissue(self, s):
        r = s.post(f"{BASE_URL}/api/integrators/{STATE['app_id']}/certificates/reissue", data={"componente": "TEST_Comp", "version_componente": "1.0"})
        if r.status_code == 200:
            STATE.setdefault("certs", []).append(r.json()["certificate_id"])
        return r

    def test_create_app(self, s):
        emp = _mongo().empresas_integradoras.find_one({}, {"_id": 0, "empresa_id": 1, "razon_social": 1})
        r = s.post(f"{BASE_URL}/api/integrators", json={
            "name": "TEST_Delta", "app_name": "TEST_DeltaApp", "integrator_type": "Integrador",
            "empresa_integradora_id": emp["empresa_id"], "implementador_user_id": IMPL_USER, "integrator_status": "En proceso"})
        assert r.status_code == 200, r.text
        STATE["app_id"] = r.json()["integrator_id"]
        print("app", r.json().get("project_scope"), r.json().get("integrator_status"))

    def test_cert1_AB(self, s):
        self._put(s, {STATE["pA"]: "C", STATE["pB"]: "C"})
        r = self._reissue(s)
        assert r.status_code == 200, r.text
        c = self._certs(s)
        assert len(c) == 1 and c[0]["status"] == "vigente"
        assert c[0]["products_included"] == ["TEST_BiopagoBDV", "TEST_ProdB_Ren"]
        app = s.get(f"{BASE_URL}/api/integrators/{STATE['app_id']}").json()
        assert set(app["cert_baseline"]) == {STATE["pA"], STATE["pB"]}

    def test_cert2_C_only(self, s):
        self._put(s, {STATE["pA"]: "C", STATE["pB"]: "C", STATE["pC"]: "C"})
        r = self._reissue(s)
        assert r.status_code == 200, r.text
        c = self._certs(s)
        assert len(c) == 2
        assert c[0]["products_included"] == ["TEST_ProdC"] and c[0]["status"] == "vigente"
        assert c[1]["status"] == "reemplazado"

    def test_no_changes_400(self, s):
        r = self._reissue(s)
        assert r.status_code == 400
        assert "No hay productos nuevos" in r.json()["detail"]
        assert len(self._certs(s)) == 2

    def test_unmark_remark_A(self, s):
        app = self._put(s, {STATE["pA"]: "N/A", STATE["pB"]: "C", STATE["pC"]: "C"})
        assert STATE["pA"] not in app["cert_baseline"]
        r = self._reissue(s)
        assert r.status_code == 400  # nothing new while A unmarked
        self._put(s, {STATE["pA"]: "C", STATE["pB"]: "C", STATE["pC"]: "C"})
        r = self._reissue(s)
        assert r.status_code == 200, r.text
        c = self._certs(s)
        assert len(c) == 3
        assert c[0]["products_included"] == ["TEST_BiopagoBDV"] and c[0]["status"] == "vigente"
        assert [x["status"] for x in c[1:]] == ["reemplazado", "reemplazado"]

    def test_download_inline_and_attachment(self, s):
        cid = STATE["certs"][-1]
        r = s.get(f"{BASE_URL}/api/integrators/certificates/{cid}/download", params={"inline": "true"})
        assert r.status_code == 200 and r.headers["content-disposition"].startswith("inline")
        assert r.content[:5] == b"%PDF-"
        r = s.get(f"{BASE_URL}/api/integrators/certificates/{cid}/download")
        assert r.headers["content-disposition"].startswith("attachment")

    def test_regression_list(self, s):
        r = s.get(f"{BASE_URL}/api/integrators")
        assert r.status_code == 200
        mine = [i for i in r.json() if i["integrator_id"] == STATE["app_id"]]
        assert mine and mine[0]["certifications"].get(STATE["pA"]) == "C"
