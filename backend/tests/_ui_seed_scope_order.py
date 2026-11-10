# UI seed for scope-order checks (TEST_ORD, RIFs J96...). Usage: python _ui_seed_scope_order.py seed|clean
import json, os, sys, uuid, asyncio
import requests
sys.path.insert(0, "/app/backend")
BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].rstrip("/") + "/api"
F = "/tmp/ord_seed.json"


def sess():
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    s.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    return s


def seed():
    s = sess(); sfx = uuid.uuid4().hex[:5].upper()
    d = {"groups": [], "brands": [], "clients": [], "quotes": []}
    g = s.post(f"{BASE}/grupos-economicos", json={"name": f"TEST_ORD Grupo {sfx}"}).json(); d["groups"].append(g["group_id"])
    nodes = []
    for bname, legal in (("Zeta", "Kiwi"), ("Alfa", "Mango"), ("Zeta", "Coco"), ("Alfa", "Banana")):
        key = f"TEST_ORD {bname} {sfx}"
        if key not in d:
            b = s.post(f"{BASE}/marcas", json={"name": key, "group_id": g["group_id"]}).json(); d["brands"].append(b["brand_id"]); d[key] = b
        b = d[key]
        c = s.post(f"{BASE}/clients", json={"rif": "J96" + str(uuid.uuid4().int)[:7], "legal_name": f"TEST_ORD {legal} {sfx} CA",
                                           "marca_id": b["brand_id"], "grupo_economico_id": g["group_id"]}).json()
        d["clients"].append(c["client_id"])
        nodes.append({"client_id": c["client_id"], "rif": c["rif"], "legal_name": c["legal_name"], "marca_id": b["brand_id"],
                      "marca_name": b["name"], "stores": [{"client_id": c["client_id"], "name": "Principal", "is_principal": True, "boxes": 2}]})
    body = {"client_id": nodes[0]["client_id"], "quote_type": "VPOS", "quote_category": "implementation", "notes": f"TEST_ORD {sfx}",
            "cantidad_cajas": 8, "nivel_cotizacion": "GRUPO", "grupo_economico_id": g["group_id"], "grupo_economico_name": g["name"],
            "scope_tree": nodes, "cajas_desglose": True, "patrocinador_tipo": "CLIENTE", "sponsored_implementation": False,
            "services": [{"item_type": "service", "item_id": "svc_test", "item_name": "TEST_ORD Servicio", "quantity": 1, "unit_price_usd": 100, "total_usd": 100}]}
    _r = s.post(f"{BASE}/quotes/create-with-pdf", json=body).json(); qid = _r.get("quote_id") or _r["quote"]["quote_id"]
    d["quotes"].append(qid)
    for st in ("Enviada", "Aprobada", "Facturada", "Pagada"):
        s.put(f"{BASE}/quotes/{qid}/status", json={"new_status": st})
    # force the stored tree of OUR quote back to unsorted order to exercise frontend sortTree
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    async def fix():
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        await db.quotes.update_one({"quote_id": qid}, {"$set": {"scope_tree": nodes}})
    asyncio.run(fix())
    d["qid"] = qid; d["sfx"] = sfx
    json.dump(d, open(F, "w")); print(json.dumps({"qid": qid, "sfx": sfx}))


def clean():
    s = sess(); d = json.load(open(F))
    projs = s.get(f"{BASE}/projects", params={"limit": 1000}).json()
    projs = projs.get("projects", projs) if isinstance(projs, dict) else projs
    for p in projs:
        if p.get("quote_id") in d["quotes"]:
            s.delete(f"{BASE}/projects/{p['project_id']}")
    for q in d["quotes"]:
        s.delete(f"{BASE}/quotes/{q}"); s.delete(f"{BASE}/quote-history/qhist_{q}")
    for c in d["clients"]:
        s.delete(f"{BASE}/clients/{c}")
    for b in d["brands"]:
        s.delete(f"{BASE}/marcas/{b}")
    for g in d["groups"]:
        s.delete(f"{BASE}/grupos-economicos/{g}")
    print("cleaned")


if __name__ == "__main__":
    seed() if sys.argv[1] == "seed" else clean()
