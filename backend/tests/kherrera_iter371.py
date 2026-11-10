# Helper iter371: reset kherrera password and toggle mass permission. Usage: reset|grant|revoke
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
from pymongo import MongoClient  # noqa: E402
from config import hash_password  # noqa: E402

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
EMAIL = "kherrera@megasoft.com.ve"
PWD = "Kherrera2026*Qa"
PERM = "clientes:mantenimiento_masivo"
cmd = sys.argv[1]
if cmd == "reset":
    db.users.update_one({"email": EMAIL}, {"$set": {"password_hash": hash_password(PWD), "must_change_password": False,
                         "password_changed_at": datetime.now(timezone.utc).isoformat(), "failed_attempts": 0, "locked_until": None}})
elif cmd == "grant":
    db.users.update_one({"email": EMAIL}, {"$addToSet": {"special_permissions": PERM}})
elif cmd == "revoke":
    db.users.update_one({"email": EMAIL}, {"$pull": {"special_permissions": PERM}})
print(cmd, db.users.find_one({"email": EMAIL}, {"_id": 0, "special_permissions": 1, "must_change_password": 1}))
