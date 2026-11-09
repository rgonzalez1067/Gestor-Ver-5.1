# Seed/cleanup helper for UI test of 'Enviar a Implementación' with scope_tree (TEST_IMPL). Usage: python _ui_seed_impl_scope.py seed|clean
import json, sys, uuid, requests
BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].rstrip("/") + "/api"
F = "/tmp/impl_seed.json"
s = requests.Session()
tok = s.post(f"{BASE}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}).json()["session_token"]
s.headers["Authorization"] = f"Bearer {tok}"


def rif():
    return "J97" + str(uuid.uuid4().int)[:7]


def create_quote(d, scope_tree, nivel, cajas, extra=None):
    body = {"client_id": d["rifA"], "quote_type": "VPOS", "quote_category": "implementation",
            "notes": f"TEST_IMPL {d['sfx']}", "cantidad_cajas": cajas, "nivel_cotizacion": nivel,
            "grupo_economico_id": d["group_id"], "grupo_economico_name": d["group_name"],
            "cajas_desglose": True, "patrocinador_tipo": "CLIENTE", "patrocinador_id": d["rifA"], "patrocinador_nombre": "TEST_IMPL",
            "sponsored_implementation": False,
            "services": [{"item_type": "service", "item_id": "svc_test", "item_name": "TEST_IMPL Servicio", "quantity": 1, "unit_price_usd": 100, "total_usd": 100}]}
    if scope_tree is not None:
        body["scope_tree"] = scope_tree
    body.update(extra or {})
    r = s.post(f"{BASE}/quotes/create-with-pdf", json=body)
    assert r.status_code == 200, r.text[:300]
    j = r.json()
    qid = j.get("quote_id") or (j.get("quote") or {}).get("quote_id")
    for st in ("Enviada", "Aprobada", "Facturada", "Pagada"):
        rr = s.put(f"{BASE}/quotes/{qid}/status", json={"new_status": st})
        assert rr.status_code == 200, f"{st} {rr.text[:200]}"
    d["quotes"].append(qid)
    return qid


if sys.argv[1] == "seed":
    sfx = uuid.uuid4().hex[:4].upper()
    d = {"sfx": sfx, "clients": [], "brands": [], "groups": [], "quotes": []}
    g = s.post(f"{BASE}/grupos-economicos", json={"name": f"TEST_IMPL Grupo {sfx}"}).json()
    d["groups"].append(g["group_id"]); d["group_id"] = g["group_id"]; d["group_name"] = g["name"]
    for k in ("A", "B"):
        b = s.post(f"{BASE}/marcas", json={"name": f"TEST_IMPL Marca {k} {sfx}", "group_id": g["group_id"]}).json()
        d["brands"].append(b["brand_id"]); d[f"brand{k}"] = b
        r = s.post(f"{BASE}/clients", json={"rif": rif(), "legal_name": f"TEST_IMPL RIF {k} {sfx} CA",
                                          "marca_id": b["brand_id"], "grupo_economico_id": g["group_id"]}).json()
        d["clients"].append(r["client_id"]); d[f"rif{k}"] = r["client_id"]; d[f"rif{k}_obj"] = r
    for n in ("S1", "S2"):
        s.post(f"{BASE}/clients/{d['rifA']}/branches", json={"sucursal": f"TEST_IMPL {n}"})
    br = s.get(f"{BASE}/clients/{d['rifA']}/branches").json()
    p = br["principal"]
    stores = [{"client_id": p.get("client_id") or d["rifA"], "name": p.get("sucursal") or "Principal", "is_principal": True}]
    stores += [{"client_id": b["client_id"], "name": b["sucursal"], "is_principal": False} for b in br["branches"]]
    d["clients"] += [b["client_id"] for b in br["branches"]]
    storesA = [dict(x, boxes=n) for x, n in zip(stores, (2, 3, 5))]
    ra, rb = d["rifA_obj"], d["rifB_obj"]
    nodeA = {"client_id": ra["client_id"], "rif": ra["rif"], "legal_name": ra["legal_name"], "marca_id": d["brandA"]["brand_id"],
             "marca_name": d["brandA"]["name"], "stores": storesA}
    nodeB = {"client_id": rb["client_id"], "rif": rb["rif"], "legal_name": rb["legal_name"], "marca_id": d["brandB"]["brand_id"],
             "marca_name": d["brandB"]["name"], "stores": [{"client_id": rb["client_id"], "name": "Principal", "is_principal": True, "boxes": 4}]}
    d["storesA"] = storesA; d["storeB"] = nodeB["stores"][0]
    d["q_mm"] = create_quote(d, [nodeA, nodeB], "GRUPO", 14)
    d["q_mt"] = create_quote(d, [nodeA], "RIF", 10)
    d["q_mono"] = create_quote(d, [dict(nodeA, stores=[dict(storesA[0], boxes=3)])], "RIF", 3)
    d["q_legacy"] = create_quote(d, None, "RIF", 2, {"cajas_desglose": False, "nivel_cotizacion": None})
    for k in ("q_mm", "q_mt", "q_mono", "q_legacy"):
        q = s.get(f"{BASE}/quotes/{d[k]}").json()
        d[k + "_num"] = q.get("quote_number")
        print(k, d[k], q.get("quote_number"), q.get("quote_status"), q.get("tipo_proyecto_inferido"), len(q.get("scope_tree") or []))
    json.dump(d, open(F, "w"))
else:
    d = json.load(open(F))
    projs = s.get(f"{BASE}/projects", params={"limit": 1000}).json()
    projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
    for p in projs:
        if p.get("quote_id") in d["quotes"]:
            print("p", p["project_id"], s.delete(f"{BASE}/projects/{p['project_id']}").status_code)
    for q in d["quotes"]:
        print("q", q, s.delete(f"{BASE}/quotes/{q}").status_code, s.delete(f"{BASE}/quote-history/qhist_{q}").status_code)
    for c in reversed(d["clients"]): print("c", s.delete(f"{BASE}/clients/{c}").status_code)
    for b in d["brands"]: print("b", s.delete(f"{BASE}/marcas/{b}").status_code)
    for g in d["groups"]: print("g", s.delete(f"{BASE}/grupos-economicos/{g}").status_code)
