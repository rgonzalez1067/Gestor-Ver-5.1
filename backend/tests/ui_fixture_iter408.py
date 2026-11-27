# UI fixture for item-reclass (iter408): python ui_fixture_iter408.py setup|teardown
import json, os, sys, uuid, requests
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
F = "/tmp/rcl_fixture.json"
s = requests.Session()
tok = s.post(f"{BASE}/api/auth/login", json={"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"}).json()["session_token"]
s.headers["Authorization"] = f"Bearer {tok}"
if sys.argv[1] == "setup":
    t = uuid.uuid4().hex[:5]
    c = {"hw": [], "movs": []}
    c["wh"] = s.post(f"{BASE}/api/inventory/warehouses", json={"name": f"TEST_RCL_UI_{t}", "location": "TEST"}).json()["warehouse_id"]
    def mk(n, ty, marca=None):
        b = {"name": f"TEST_RCLUI_{n}_{t}", "type": ty, "price_usd": 5, "price_bs_usd": 5}
        if marca: b["marca"] = marca
        h = s.post(f"{BASE}/api/hardware", json=b).json()["hardware_id"]; c["hw"].append(h); return h
    c["ns_a"], c["ns_b"] = mk("ACC_A", "Accesorio"), mk("ACC_B", "Accesorio")
    c["s_a"], c["s_b"] = mk("POS_A", "POS", "Verifone"), mk("POS_B", "POS", "Verifone")
    c["serials"] = [f"TUI{t}{i}" for i in range(3)]
    for iid, q, ser in ((c["ns_a"], 6, []), (c["s_a"], 3, c["serials"])):
        c["movs"].append(s.post(f"{BASE}/api/inventory/warehouses/{c['wh']}/entry", json={"item_id": iid, "quantity": q, "unit_cost": 10, "serials": ser}).json()["movement_id"])
    c["token"] = tok
    json.dump(c, open(F, "w")); print(json.dumps(c))
else:
    c = json.load(open(F))
    for iid in (c["ns_a"], c["ns_b"], c["s_a"], c["s_b"]):
        k = s.get(f"{BASE}/api/inventory/warehouses/{c['wh']}/kardex/{iid}").json()
        for m in k.get("movements", []):
            s.delete(f"{BASE}/api/inventory/movements/{m['movement_id']}")
    print(s.delete(f"{BASE}/api/inventory/warehouses/{c['wh']}").status_code)
    for h in c["hw"]:
        print(s.delete(f"{BASE}/api/hardware/{h}").status_code)
