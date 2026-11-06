import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
async def m():
    ids = await db.quotes.distinct("client_id", {"archived": {"$ne": True}})
    n = 0
    async for c in db.clients.find({"client_id": {"$in": ids}}, {"_id": 0, "client_id": 1, "legal_name": 1, "fantasy_name": 1}):
        if c.get("fantasy_name") and c.get("fantasy_name", "").upper() != (c.get("legal_name") or "").upper():
            cnt = await db.quotes.count_documents({"client_id": c["client_id"], "archived": {"$ne": True}})
            print(c, cnt); n += 1
            if n > 6: break
    print("clients total", await db.clients.count_documents({}))
asyncio.run(m())
