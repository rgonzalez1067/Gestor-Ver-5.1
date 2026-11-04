# Iter 352 UI fixture: set/restore phases of Banco del Tesoro products. Usage: python ui_fixture_iter352.py set|restore|login
import sys, json, requests
BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/") + "/api"
BANK_ID = "bnk_91d0cba04375"
s = requests.Session()
d = s.post(f"{BASE}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"}).json()
s.headers["Authorization"] = f"Bearer {d['session_token']}"
mode = sys.argv[1]
if mode == "login":
    print(json.dumps({"token": d["session_token"], "user": d.get("user")}))
    sys.exit()
bank = next(b for b in s.get(f"{BASE}/banks").json() if b["bank_id"] == BANK_ID)
target = {"set": "SQA", "restore": "Imple", "desa": "DESA"}[mode]
for p in bank["products"]:
    if p["product_name"] == "Cambio Pago Movil ":
        p["operational_status"] = target
r = s.put(f"{BASE}/banks/{BANK_ID}", json=bank, timeout=30)
print(r.status_code, [(p["product_name"], p["operational_status"]) for p in r.json()["products"]])
