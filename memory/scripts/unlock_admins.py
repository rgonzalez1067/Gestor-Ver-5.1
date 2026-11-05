import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
async def m():
    r = await db.users.update_many({"email": {"$in": ["rgonzalez@megasoft.com.ve", "dcollazo@megasoft.com.ve"]}},
                                   {"$set": {"failed_login_attempts": 0, "lockout_timestamp": None}, "$unset": {"locked_until": ""}})
    print(r.modified_count)
asyncio.run(m())
