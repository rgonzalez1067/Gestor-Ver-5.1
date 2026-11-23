# Fixture: create/remove one TEST_ unread inbox message for QA admin (user_qaintegr01) to exercise the unread banner
import asyncio, os, sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv('/app/backend/.env')
MID = "TEST_msg_iter392_uialerts"


async def main(cmd):
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    if cmd == "setup":
        await db.inbox_messages.update_one({"message_id": MID}, {"$set": {
            "message_id": MID, "user_id": "user_qaintegr01", "deleted_at": None, "read_at": None,
            "is_user_message": False, "title": "TEST_ aviso QA", "message": "TEST_ iter392", "priority": "low",
            "type": "info", "created_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    else:
        r = await db.inbox_messages.delete_one({"message_id": MID})
        print("deleted", r.deleted_count)


asyncio.run(main(sys.argv[1]))
