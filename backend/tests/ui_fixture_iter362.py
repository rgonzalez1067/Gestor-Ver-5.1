# ruff: noqa
"""Iter362 UI fixture: crea una cotización MPOS TEST_ y emite token/user JSON. Uso: python ui_fixture_iter362.py [create|cleanup <qid>]"""
import os, sys, json, uuid, requests
from pymongo import MongoClient
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
if sys.argv[1] == "create":
    r = requests.post(f"{BASE}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}).json()
    H = {"Authorization": "Bearer " + r["session_token"]}
    cl = next(c for c in requests.get(f"{BASE}/api/clients", headers=H).json() if c.get("rif") and not c.get("is_placeholder"))
    q = requests.post(f"{BASE}/api/quotes", headers=H, json={
        "client_id": cl["client_id"], "quote_category": "implementation", "quote_type": "MPOS",
        "services": [{"item_id": "svc_" + uuid.uuid4().hex[:8], "item_name": "TEST_ITER362_UI", "item_type": "setup",
                      "unit_price_usd": 100.0, "quantity": 1, "total_usd": 100.0, "cantidad_cajas": 1, "cantidad_bancos": 1}],
        "hardware": [], "equipment_items": [], "cantidad_cajas": 1, "cantidad_bancos": 1,
        "notes": "TEST_ITER362_UI", "client_segment": "PYME"}).json()
    print(json.dumps({"token": r["session_token"], "user": r["user"], "quote_id": q["quote_id"], "quote_number": q["quote_number"]}))
else:
    for qid in sys.argv[2:]:
        db.projects.delete_many({"quote_id": qid}); db.quote_history.delete_many({"quote_id": qid}); db.quotes.delete_one({"quote_id": qid})
    print("cleaned")
