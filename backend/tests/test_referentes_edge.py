# Referentes edge cases: permission-granted non-admin, inactive/merged reuse
import os, uuid, requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
SUF = uuid.uuid4().hex[:6]


def login(e, p):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": e, "password": p}).json()
    s.headers["Authorization"] = f"Bearer {r['session_token']}"
    s.user = r["user"]
    return s


a = login("qa.integradores@megasoft.com.ve", "QaIntegr2026*Ok")
contacts, refs = [], []
orig = db.users.find_one({"email": "qa.editor@megasoft.com.ve"}, {"_id": 0, "special_permissions": 1}).get("special_permissions")
try:
    db.users.update_one({"email": "qa.editor@megasoft.com.ve"}, {"$addToSet": {"special_permissions": "referentes:crear"}})
    e = login("qa.editor@megasoft.com.ve", "QaIntegr2026*Ok")
    g = e.get(f"{BASE}/api/referentes").json()
    print("editor with perm can_create:", g["can_create"])
    r = e.post(f"{BASE}/api/referentes", json={"nombre_referente": f"TEST_EdPerm_{SUF}", "tipo_referente": "AREA"})
    print("editor POST referentes:", r.status_code)
    if r.status_code == 200: refs.append(r.json()["referente_id"])
    r = e.post(f"{BASE}/api/initial-contacts", json={"contact_name": f"TEST_C_{SUF}", "legal_name": "TEST_L", "assigned_to_user_id": e.user["user_id"],
                                                     "nuevo_referente": {"nombre_referente": f"TEST_EdQuick_{SUF}", "tipo_referente": "PERSONA"}})
    print("editor POST contact nuevo_referente:", r.status_code, r.text[:150])
    if r.status_code == 200:
        contacts.append(r.json()["contact_id"]); refs.append(r.json()["referente_id"])
    print("editor PUT referente:", e.put(f"{BASE}/api/referentes/{refs[0]}", json={"empresa": "x"}).status_code if refs else None)
finally:
    db.users.update_one({"email": "qa.editor@megasoft.com.ve"}, {"$set": {"special_permissions": orig or []}})

# inactive reuse via quick-create
x = a.post(f"{BASE}/api/referentes", json={"nombre_referente": f"TEST_Inact_{SUF}", "tipo_referente": "PERSONA"}).json(); refs.append(x["referente_id"])
a.put(f"{BASE}/api/referentes/{x['referente_id']}", json={"estatus": False})
r = a.post(f"{BASE}/api/initial-contacts", json={"contact_name": f"TEST_C2_{SUF}", "legal_name": "TEST_L", "assigned_to_user_id": a.user["user_id"],
                                                 "nuevo_referente": {"nombre_referente": f"TEST_Inact_{SUF}", "tipo_referente": "PERSONA"}}).json()
contacts.append(r["contact_id"])
st = db.referentes.find_one({"referente_id": r["referente_id"]}, {"_id": 0, "estatus": 1})
print("quick-create w/ inactive name -> linked to", r["referente_id"], "same as inactive:", r["referente_id"] == x["referente_id"], "estatus:", st)
r = a.post(f"{BASE}/api/initial-contacts", json={"contact_name": f"TEST_C3_{SUF}", "legal_name": "TEST_L", "assigned_to_user_id": a.user["user_id"],
                                                 "referente_id": x["referente_id"]})
print("contact w/ inactive referente_id:", r.status_code)
if r.status_code == 200: contacts.append(r.json()["contact_id"])
# edit: clear referente
cid = contacts[-1]
r = a.put(f"{BASE}/api/initial-contacts/{cid}", json={"referente_id": ""})
c = db.initial_contacts.find_one({"contact_id": cid}, {"_id": 0, "referente_id": 1})
print("edit clear referente ->", r.status_code, c)
# free text referred_by bypass
r = a.post(f"{BASE}/api/initial-contacts", json={"contact_name": f"TEST_C4_{SUF}", "legal_name": "TEST_L", "assigned_to_user_id": a.user["user_id"], "referred_by": "TEST_FreeText"}).json()
contacts.append(r["contact_id"]); print("free text referred_by stored:", r.get("referred_by"), r.get("referente_id"))
# audit for UPDATE
import time; time.sleep(1)
au = a.get(f"{BASE}/api/audit-trails", params={"modules": "Referentes", "page_size": 20}).json()["items"]
print("audit actions:", sorted({i.get("accion") or i.get("action") for i in au}))

for c in contacts: a.delete(f"{BASE}/api/initial-contacts/{c}")
for rf in refs: a.put(f"{BASE}/api/referentes/{rf}", json={"estatus": False})
print("cleanup done; editor perms restored:", db.users.find_one({"email": "qa.editor@megasoft.com.ve"}, {"_id": 0, "special_permissions": 1}))
