import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
async def m():
    hw = set(await db.hardware.distinct("hardware_id"))
    for c in ["inventory_movements", "serial_assignments", "temporary_assignments", "serial_blacklist", "taller_equipos"]:
        d = await db[c].find_one({}, {"_id": 0})
        print(c, sorted((d or {}).keys()))
        if d and "item_id" in d:
            ids = await db[c].distinct("item_id")
            print("  orphans:", [i for i in ids if i not in hw])
asyncio.run(m())
