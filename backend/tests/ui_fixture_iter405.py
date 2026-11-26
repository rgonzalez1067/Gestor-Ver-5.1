# Iter405 UI fixture: create/cleanup a TEST_ integrator with C products for the expansion request-matrix UI test
import os, sys, json, uuid, requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
B = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
s = requests.Session()
tok = s.post(f"{B}/api/auth/login", json={"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"}).json()["session_token"]
s.headers["Authorization"] = f"Bearer {tok}"
F = "/tmp/iter405_fixture.json"

if sys.argv[1] == "create":
    name = f"TEST_UIExp_{uuid.uuid4().hex[:5]}"
    r = s.post(f"{B}/api/integrators", json={"name": name, "integrator_type": "Integrador", "integration_type": "CR",
               "app_name": "TEST_UIApp", "integration_modality": "Rest", "contacts": [{"name": "TEST Resp", "email": "test_resp@example.com"}]}).json()
    iid = r["integrator_id"]
    prods = s.get(f"{B}/api/integrators/products").json()
    certs = {p["service_id"]: "N/A" for p in prods}
    certs.update({"prod_tdd_tdc": "C", "prod_c2p": "C", "prod_verificacion_p2c": "P"})
    cur = s.get(f"{B}/api/integrators/{iid}").json()
    body = {k: cur.get(k) for k in ("name", "integrator_type", "integration_type", "app_name", "integration_modality", "contacts")}
    body.update({"certifications": certs, "integrator_status": "En proceso"})
    print(s.put(f"{B}/api/integrators/{iid}", json=body).status_code)
    d = s.get(f"{B}/api/integrators/{iid}").json()
    json.dump({"iid": iid, "name": d["name"], "emp": d.get("empresa_integradora_id")}, open(F, "w"))
    print(json.dumps({"iid": iid, "name": d["name"], "emp": d.get("empresa_integradora_id")}))
elif sys.argv[1] == "show":
    d = s.get(f"{B}/api/integrators/{json.load(open(F))['iid']}").json()
    print(json.dumps({k: d.get(k) for k in ("project_scope", "integrator_status", "productos_certificar", "correo_eventual", "cert_baseline")}))
    print({k: v for k, v in (d.get("certifications") or {}).items() if v != "N/A"})
elif sys.argv[1] == "reset":
    # put back to scope new-like baseline state for re-test (only our record)
    fx = json.load(open(F))
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    prods = s.get(f"{B}/api/integrators/products").json()
    certs = {p["service_id"]: "N/A" for p in prods}
    certs.update({"prod_tdd_tdc": "C", "prod_c2p": "C", "prod_verificacion_p2c": "P"})
    db.integrators.update_one({"integrator_id": fx["iid"]}, {"$set": {"certifications": certs, "project_scope": "new", "productos_certificar": None}})
    print("reset")
elif sys.argv[1] == "cleanup":
    fx = json.load(open(F))
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    db.integrator_certificates.delete_many({"integrator_id": fx["iid"]})
    print(s.delete(f"{B}/api/integrators/{fx['iid']}").status_code)
    if fx.get("emp") and not db.integrators.count_documents({"empresa_integradora_id": fx["emp"]}):
        print(db.empresas_integradoras.delete_one({"empresa_id": fx["emp"], "razon_social": {"$regex": "^TEST_"}}).deleted_count)
