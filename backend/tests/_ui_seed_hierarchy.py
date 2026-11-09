# UI seed/cleanup helper for 4-level hierarchy QA. Usage: python _ui_seed_hierarchy.py seed|clean
import json, sys, uuid, requests
API = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0].rstrip('/') + '/api'
F = '/tmp/qa4n_ui.json'
s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}).json()
s.headers["Authorization"] = f"Bearer {r['session_token']}"
ok = lambda r: (r.raise_for_status() or r.json())
if sys.argv[1] == 'seed':
    X = uuid.uuid4().hex[:4].upper()
    rif = lambda: "J99" + str(uuid.uuid4().int)[:7]
    g = ok(s.post(f"{API}/grupos-economicos", json={"name": f"QA4N UI Grupo {X}", "contacts": [{"full_name": "Corp A", "email": "corpa@qa4n.com"}],
              "characteristics": {"segment": "Corporativo", "categoria_comercial": "Retail"}}))
    ba = ok(s.post(f"{API}/marcas", json={"name": f"QA4N UI Marca A {X}", "group_id": g["group_id"]}))
    bb = ok(s.post(f"{API}/marcas", json={"name": f"QA4N UI Marca B {X}", "group_id": g["group_id"], "contacts": [{"full_name": "Marca B", "email": "mb@qa4n.com"}]}))
    a1 = ok(s.post(f"{API}/clients", json={"rif": rif(), "legal_name": f"QA4N UI RIF UNO {X}", "marca_id": ba["brand_id"], "grupo_economico_id": g["group_id"], "segment": "Corporativo",
               "contacts": [{"full_name": "Rif Uno", "email": "r1@qa4n.com"}]}))
    a2 = ok(s.post(f"{API}/clients", json={"rif": rif(), "legal_name": f"QA4N UI RIF DOS {X}", "marca_id": ba["brand_id"], "grupo_economico_id": g["group_id"], "segment": "Corporativo"}))
    for n in ("S1", "S2", "S3"):
        body = {"sucursal": n}
        if n == "S3": body["contacts"] = [{"full_name": "Local C", "email": "lc@qa4n.com"}]
        ok(s.post(f"{API}/clients/{a1['client_id']}/branches", json=body))
    brs = ok(s.get(f"{API}/clients/{a1['client_id']}/branches"))["branches"]
    d = {"X": X, "g": g["group_id"], "gname": g["name"], "ba": ba["brand_id"], "baname": ba["name"], "bb": bb["brand_id"],
         "a1": a1["client_id"], "a1rif": a1["rif"], "a2": a2["client_id"], "branches": [b["client_id"] for b in brs], "extra_clients": [], "extra_brands": []}
    json.dump(d, open(F, 'w')); print(json.dumps(d))
else:
    d = json.load(open(F))
    for cid in d["branches"] + [d["a1"], d["a2"]] + d.get("extra_clients", []):
        print(cid, s.delete(f"{API}/clients/{cid}").status_code)
    for bid in [d["ba"], d["bb"]] + d.get("extra_brands", []):
        print(bid, s.delete(f"{API}/marcas/{bid}").status_code)
    print('g', s.delete(f"{API}/grupos-economicos/{d['g']}").status_code)
