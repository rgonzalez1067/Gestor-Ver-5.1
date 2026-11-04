"""Setup/teardown fixtures for iter346 UI test (copy_emails). Usage: python ui_fixtures_iter346.py setup|teardown|logs"""
import os, sys, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
BK = "bnk_TEST_ui346"
INT = "int_TEST_ui346"
TPLS = ["tpl_TEST_ui346_c", "tpl_TEST_ui346_n"]


async def main(op):
    c = AsyncIOMotorClient(os.environ["MONGO_URL"]); db = c[os.environ["DB_NAME"]]
    if op == "setup":
        await db.banks.insert_one({"bank_id": BK, "name": "TEST_UI346 BANCO", "rif": "J-346", "contacts": [
            {"full_name": "TEST Uno", "email": "uno_ui346@example.com", "position": "G"},
            {"full_name": "TEST Dos", "email": "dos_ui346@example.com", "position": "A"}]})
        await db.integrators.insert_one({"integrator_id": INT, "name": "TEST_UI346 INTEGRADOR", "email": "int_ui346@example.com", "integration_type": "API"})
        await db.email_templates.insert_many([
            {"template_id": TPLS[0], "context": "INTEGRADORES", "name": "TEST_UI346 Contacto", "subject": "TEST_UI346 {contacto_nombre}", "body_html": "<p>x</p>"},
            {"template_id": TPLS[1], "context": "INTEGRADORES", "name": "TEST_UI346 Simple", "subject": "TEST_UI346 S", "body_html": "<p>x</p>"}])
    elif op == "logs":
        async for l in db.email_logs.find({"subject": {"$regex": "^TEST_UI346"}}, {"_id": 0, "to": 1, "bcc_count": 1, "subject": 1, "action": 1}).sort("created_at", 1):
            print(l)
        async for b in db.bitacora.find({"template_id": {"$in": TPLS}}, {"_id": 0, "action": 1, "copy_emails": 1, "send_mode": 1}):
            print("BIT", b)
    else:
        await db.banks.delete_one({"bank_id": BK})
        await db.integrators.delete_one({"integrator_id": INT})
        r = await db.email_templates.delete_many({"template_id": {"$in": TPLS}})
        b = await db.bitacora.delete_many({"template_id": {"$in": TPLS}})
        e = await db.email_logs.delete_many({"subject": {"$regex": "^TEST_UI346"}})
        print("deleted tpl", r.deleted_count, "bit", b.deleted_count, "logs", e.deleted_count)
    c.close()

asyncio.run(main(sys.argv[1]))
