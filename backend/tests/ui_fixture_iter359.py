# UI fixture for security policy (iter359): `python ui_fixture_iter359.py setup|cleanup|lock <uid>|force2fa|policy2fa on/off`
import os, sys, json, uuid, hashlib
from datetime import datetime, timezone, timedelta
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
STATE = "/tmp/ui_iter359.json"
PWD = "TestAlpha#2026x"


def admin_h():
    t = requests.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}).json()["session_token"]
    return {"Authorization": f"Bearer {t}"}


def mk(h, tag):
    email = f"test_ui_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{API}/admin/users/create", headers=h, json={"first_name": "TEST_UI", "last_name": tag.capitalize(), "email": email, "password": PWD, "sede": "PYME"})
    assert r.status_code in (200, 201), r.text
    return {"email": email, "uid": mdb.users.find_one({"email": email})["user_id"]}


cmd = sys.argv[1]
now = datetime.now(timezone.utc)
if cmd == "setup":
    h = admin_h()
    st = {k: mk(h, k) for k in ["normal", "warn", "expired", "twofa", "locked"]}
    mdb.users.update_one({"user_id": st["warn"]["uid"]}, {"$set": {"password_changed_at": (now - timedelta(days=85)).isoformat()}})
    mdb.users.update_one({"user_id": st["expired"]["uid"]}, {"$set": {"password_changed_at": (now - timedelta(days=100)).isoformat()}})
    mdb.users.update_one({"user_id": st["locked"]["uid"]}, {"$set": {"account_status": "LOCKED", "failed_login_attempts": 5, "lockout_timestamp": now.isoformat()}})
    json.dump(st, open(STATE, "w")); print(json.dumps(st))
elif cmd == "force2fa":
    st = json.load(open(STATE))
    r = mdb.login_2fa_challenges.update_many({"user_id": st["twofa"]["uid"]}, {"$set": {"code_hash": hashlib.sha256(b"246810").hexdigest()}})
    print("forced", r.modified_count)
elif cmd == "policy2fa":
    mdb.security_policies.update_one({"policy_id": "global"}, {"$set": {"two_factor_enabled": sys.argv[2] == "on"}})
    print(mdb.security_policies.find_one({"policy_id": "global"}, {"_id": 0, "two_factor_enabled": 1}))
elif cmd == "cleanup":
    st = json.load(open(STATE))
    for v in st.values():
        uid = v["uid"]
        for c in ["users", "user_password_history", "user_sessions", "login_2fa_challenges", "password_change_tokens"]:
            mdb[c].delete_many({"user_id": uid})
    h = admin_h()
    requests.put(f"{API}/admin/security-policy", headers=h, json={"password_max_age_days": 90, "expiry_warning_days": 7, "password_history_count": 5,
                 "max_failed_attempts": 5, "lockout_minutes": 15, "two_factor_enabled": False, "min_password_length": 12, "otp_ttl_minutes": 10})
    print("cleaned", mdb.security_policies.find_one({"policy_id": "global"}, {"_id": 0}))
