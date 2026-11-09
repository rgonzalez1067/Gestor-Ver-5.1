# Seed/cleanup helper for UI test of quote scope (TEST_QS). Usage: python _ui_seed_quote_scope.py seed|clean
import json, sys, uuid, requests
BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].rstrip("/") + "/api"
F = "/tmp/qs_seed.json"
s = requests.Session()
tok = s.post(f"{BASE}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}).json()["session_token"]
s.headers["Authorization"] = f"Bearer {tok}"
if sys.argv[1] == "seed":
    sfx = uuid.uuid4().hex[:4].upper()
    d = {"clients": [], "brands": [], "groups": []}
    g = s.post(f"{BASE}/grupos-economicos", json={"name": f"AAA TEST_QS Grupo {sfx}"}).json(); d["groups"].append(g["group_id"])
    d["group_id"] = g["group_id"]
    for k in ("A", "B"):
        b = s.post(f"{BASE}/marcas", json={"name": f"TEST_QS Marca {k} {sfx}", "group_id": g["group_id"]}).json()
        d["brands"].append(b["brand_id"]); d[f"brand{k}"] = b["name"]
        r = s.post(f"{BASE}/clients", json={"rif": "J98" + str(uuid.uuid4().int)[:7], "legal_name": f"TEST_QS RIF {k} {sfx} CA",
                                          "marca_id": b["brand_id"], "grupo_economico_id": g["group_id"]}).json()
        d["clients"].append(r["client_id"]); d[f"rif{k}"] = r["client_id"]
    for n in ("S1", "S2"):
        s.post(f"{BASE}/clients/{d['rifA']}/branches", json={"sucursal": f"TEST_QS {n}"})
    br = s.get(f"{BASE}/clients/{d['rifA']}/branches").json()
    d["storesA"] = [br["principal"].get("client_id") or d["rifA"]] + [b["client_id"] for b in br["branches"]]
    d["clients"] += [b["client_id"] for b in br["branches"]]
    json.dump(d, open(F, "w")); print(json.dumps(d))
else:
    d = json.load(open(F))
    for c in reversed(d["clients"]): print("c", s.delete(f"{BASE}/clients/{c}").status_code)
    for b in d["brands"]: print("b", s.delete(f"{BASE}/marcas/{b}").status_code)
    for g in d["groups"]: print("g", s.delete(f"{BASE}/grupos-economicos/{g}").status_code)
