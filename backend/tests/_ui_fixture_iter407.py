# Iter407 UI fixture: python _ui_fixture_iter407.py create|delete
import os, sys, json, requests
BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].rstrip("/")
STATE = "/tmp/iter407_ui.json"
h = {"Authorization": "Bearer " + requests.post(f"{BASE}/api/auth/login", json={"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"}).json()["session_token"]}
if sys.argv[1] == "create":
    q1 = requests.post(f"{BASE}/api/quotes", headers=h, json={"client_id": "cli_05f6268761c7", "quote_category": "implementation", "quote_type": "VPOS", "notes": "TEST_iter407 UI"}).json()
    refs = requests.get(f"{BASE}/api/referentes", headers=h).json()
    refs = refs if isinstance(refs, list) else refs.get("items", [])
    c = requests.post(f"{BASE}/api/initial-contacts", headers=h, json={"contact_name": "TEST_iter407 UI Contacto", "legal_name": "TEST_ITER407 UI CA", "referente_id": refs[0]["referente_id"]}).json()
    st = {"quote_id": q1["quote_id"], "quote_number": q1["quote_number"], "contact_id": c["contact_id"], "ref0": refs[0]["nombre_referente"], "ref1": refs[1]["nombre_referente"]}
    json.dump(st, open(STATE, "w")); print(st)
else:
    st = json.load(open(STATE))
    print(requests.delete(f"{BASE}/api/quote-history/qhist_{st['quote_id']}", headers=h).status_code,
          requests.delete(f"{BASE}/api/quotes/{st['quote_id']}", headers=h).status_code,
          requests.delete(f"{BASE}/api/initial-contacts/{st['contact_id']}", headers=h).status_code)
