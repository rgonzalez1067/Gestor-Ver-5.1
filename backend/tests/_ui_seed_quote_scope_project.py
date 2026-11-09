# UI helper: create Multi Marca project from seeded TEST_QS data (python _ui_seed_quote_scope_project.py make|clean)
import json, sys, requests
BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].rstrip("/") + "/api"
F = "/tmp/qs_seed.json"
d = json.load(open(F))
s = requests.Session()
s.headers["Authorization"] = "Bearer " + s.post(f"{BASE}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}).json()["session_token"]
if sys.argv[1] == "make":
    cA = s.get(f"{BASE}/clients/{d['rifA']}").json(); cB = s.get(f"{BASE}/clients/{d['rifB']}").json()
    tree = [{"client_id": d["rifA"], "rif": cA.get("rif"), "legal_name": cA.get("legal_name"), "marca_id": d["brands"][0], "marca_name": d["brandA"],
             "stores": [{"client_id": x, "name": f"T{i}", "boxes": i + 1} for i, x in enumerate(d["storesA"])]},
            {"client_id": d["rifB"], "rif": cB.get("rif"), "legal_name": cB.get("legal_name"), "marca_id": d["brands"][1], "marca_name": d["brandB"],
             "stores": [{"client_id": d["rifB"], "name": "Principal", "boxes": 4}]}]
    r = s.post(f"{BASE}/quotes/create-with-pdf", json={"client_id": d["rifA"], "quote_type": "VPOS", "notes": "TEST_QS ui", "cantidad_cajas": 10,
        "nivel_cotizacion": "GRUPO", "grupo_economico_id": d["group_id"], "scope_tree": tree, "cajas_desglose": True,
        "patrocinador_tipo": "CLIENTE", "patrocinador_id": d["rifB"], "patrocinador_nombre": cB.get("legal_name"),
        "services": [{"item_type": "service", "item_name": "TEST_QS", "quantity": 1, "unit_price_usd": 10, "total_usd": 10}]})
    j = r.json(); qid = j.get("quote_id") or j["quote"]["quote_id"]
    for st in ("Enviada", "Aprobada", "Facturada", "Pagada", "Enviada a Imple"):
        s.put(f"{BASE}/quotes/{qid}/status", json={"new_status": st})
    projs = s.get(f"{BASE}/projects", params={"limit": 500}).json()
    projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
    p = next(x for x in projs if x.get("quote_id") == qid)
    d["project_id"] = p["project_id"]; d["quote_id"] = qid
    json.dump(d, open(F, "w")); print(p["project_id"], p.get("project_number") or p.get("name"))
else:
    print(s.delete(f"{BASE}/projects/{d['project_id']}").status_code, s.delete(f"{BASE}/quote-history/qhist_{d['quote_id']}").status_code)
