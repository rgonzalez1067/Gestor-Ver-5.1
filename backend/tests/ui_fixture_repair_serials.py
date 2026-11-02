# Setup/teardown fixture for UI testing of repair serials editing. Usage: python ui_fixture_repair_serials.py setup|teardown SUF
import os, sys, uuid, json, requests
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
mdb = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
mode, SUF = sys.argv[1], sys.argv[2]
S1, S2, S3 = f"TST-U1-{SUF}", f"TST-U2-{SUF}", f"TST-U3-{SUF}"

if mode == "setup":
    tok = requests.post(f"{BASE}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "admin123"}).json()
    h = {"Authorization": f"Bearer {tok.get('session_token') or tok.get('token')}"}
    r = requests.post(f"{BASE}/api/clients", headers=h, json={"rif": f"J-{uuid.uuid4().int % 10**8:08d}-2",
                      "legal_name": f"TEST_UI Cliente {SUF}", "fantasy_name": f"TEST_UI Cliente {SUF}"}).json()
    cid = r.get("client_id") or r["client"]["client_id"]
    requests.post(f"{BASE}/api/taller/recepcion", headers=h, json={"client_id": cid, "models": [
        {"model_name": "TEST Modelo", "serials": [S1, S2, S3]}]}).raise_for_status()
    ids = [mdb.taller_equipos.find_one({"serial": s})["taller_equipo_id"] for s in (S1, S2)]
    it = lambda n, q, s: {"name": n, "quantity": q, "unit_price_usd": 10, "total_usd": 10 * q, "serials": s}
    r = requests.post(f"{BASE}/api/quotes/generate-equipment-pdf", headers=h, json={
        "client_id": cid, "cliente_nombre": f"TEST_UI Cliente {SUF}", "equipment_type": "Reparación",
        "items": [it("TEST Servicio A", 2, [S1, S2]), it("TEST Servicio B", 1, [S1])],
        "repair_models": [{"model_name": "TEST Modelo", "quantity": 2, "serials": [S1, S2]}],
        "linked_taller_equipo_ids": ids})
    r.raise_for_status()
    print(json.dumps({"client_id": cid, "quote_id": r.headers["X-Quote-Id"], "quote_number": r.headers["X-Quote-Number"]}))
else:
    cids = [c["client_id"] for c in mdb.clients.find({"legal_name": f"TEST_UI Cliente {SUF}"})]
    qs = [x["quote_id"] for x in mdb.quotes.find({"client_id": {"$in": cids}})]
    print("deleted quotes", mdb.quotes.delete_many({"quote_id": {"$in": qs}}).deleted_count)
    print("deleted te", mdb.taller_equipos.delete_many({"serial": {"$regex": f"^TST-U.*{SUF}$"}}).deleted_count)
    print("deleted clients", mdb.clients.delete_many({"client_id": {"$in": cids}}).deleted_count)
    mdb.client_logs.delete_many({"client_id": {"$in": cids}})
