# Iter407: create/delete TEST_ non-admin user (python _iter407_test_user.py create|delete)
import sys, os, asyncio
from datetime import datetime, timezone
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient
from config import hash_password

EMAIL = "test_iter407_user@example.com"


async def main(cmd):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    if cmd == "create":
        now = datetime.now(timezone.utc).isoformat()
        await db.users.delete_one({"email": EMAIL})
        await db.users.insert_one({
            "user_id": "user_test_iter407", "email": EMAIL, "first_name": "TEST_iter407", "last_name": "User",
            "name": "TEST_iter407 User", "cargo": "Coordinador", "departamento": "Ventas Pyme",
            "password_hash": hash_password("TestIter407*Pwd!"), "role": "user", "sede": "PYME",
            "is_active": True, "is_verified": True, "permissions": {"cotizaciones": "edit", "contactos_iniciales": "edit"},
            "special_permissions": [], "must_change_password": False, "password_changed_at": now,
            "failed_login_attempts": 0, "account_status": "active", "created_at": now})
        print("created")
    else:
        r = await db.users.delete_one({"email": EMAIL})
        await db.user_sessions.delete_many({"user_id": "user_test_iter407"})
        print("deleted", r.deleted_count)

asyncio.run(main(sys.argv[1]))
