# Read-only check of rgonzalez account state + offline password verification (no login attempt)
import asyncio, os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    u = await db.users.find_one({"email": "rgonzalez@megasoft.com.ve"}, {"_id": 0})
    if not u:
        print("USER NOT FOUND"); return
    keys = ["user_id", "role", "account_status", "failed_login_attempts", "lockout_timestamp",
            "must_change_password", "password_changed_at", "two_factor_enabled", "is_active", "status"]
    for k in keys:
        print(k, "=", u.get(k))
    h = u.get("password_hash") or u.get("password")
    from config import verify_password
    print("password_match =", verify_password("MegaSoft2026*", h))
    pol = await db.security_policy.find_one({}, {"_id": 0}) if "security_policy" in await db.list_collection_names() else None
    print("policy_doc =", pol)

asyncio.run(main())
