# Inspect projects created from TEST_IMPL quotes (reads /tmp/impl_seed.json)
import json, requests
BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].rstrip("/") + "/api"
s = requests.Session()
s.headers["Authorization"] = "Bearer " + s.post(f"{BASE}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}).json()["session_token"]
d = json.load(open("/tmp/impl_seed.json"))
projs = s.get(f"{BASE}/projects", params={"limit": 1000}).json()
projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
for k in ("q_mm", "q_mt", "q_mono", "q_legacy"):
    p = next((x for x in projs if x.get("quote_id") == d[k]), None)
    if not p:
        print(k, "no project"); continue
    p = s.get(f"{BASE}/projects/{p['project_id']}").json()
    print(k, p["project_id"], p.get("project_number"), "tipologia=", p.get("tipologia_proyecto"), "type=", p.get("project_type"),
          "rifs=", [(r.get("rif"), r.get("marca_name"), r.get("box_count")) for r in p.get("rifs") or []])
    print("   stores=", [(st.get("name"), st.get("marca_name"), st.get("box_count")) for st in p.get("stores") or []],
          "server=", p.get("server_name"), "fiscal=", p.get("fiscal_printer_model"), "egroup=", p.get("economic_group"))
    q = s.get(f"{BASE}/quotes/{d[k]}")
    print("   quote still active?", q.status_code)
