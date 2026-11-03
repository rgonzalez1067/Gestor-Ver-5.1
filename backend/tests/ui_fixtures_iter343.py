"""Setup/teardown fixtures for iter343 UI test. Usage: python ui_fixtures_iter343.py setup|teardown"""
import os, sys, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
BK = "bnk_TEST_ui343"
TPLS = ["tpl_TEST_ui343_c", "tpl_TEST_ui343_b", "tpl_TEST_ui343_n"]


async def main(op):
    c = AsyncIOMotorClient(os.environ["MONGO_URL"]); db = c[os.environ["DB_NAME"]]
    if op == "setup":
        await db.banks.insert_one({"bank_id": BK, "name": "TEST_UI343 BANCO", "rif": "J-343", "contacts": [
            {"full_name": "TEST Uno", "email": "uno_ui343@example.com", "position": "G"},
            {"full_name": "TEST Dos", "email": "dos_ui343@example.com", "position": "A"}]})
        await db.email_templates.insert_many([
            {"template_id": TPLS[0], "context": "INTEGRADORES", "name": "TEST_UI343 Contacto", "subject": "TEST_UI343 {contacto_nombre}", "body_html": "<p>x</p>"},
            {"template_id": TPLS[1], "context": "INTEGRADORES", "name": "TEST_UI343 Banco", "subject": "TEST_UI343 B", "body_html": "<p>{{banco_nombre}}</p>"},
            {"template_id": TPLS[2], "context": "INTEGRADORES", "name": "TEST_UI343 Simple", "subject": "TEST_UI343 S", "body_html": "<p>x</p>"}])
    else:
        await db.banks.delete_one({"bank_id": BK})
        r = await db.email_templates.delete_many({"$or": [{"template_id": {"$in": TPLS}}, {"name": {"$regex": "^TEST_UI343"}, "context": "INTEGRADORES"}]})
        b = await db.bitacora.delete_many({"action": "bank_mass_communication", "bank_ids": BK})
        e = await db.email_logs.delete_many({"action": "bank_mass_communication", "subject": {"$regex": "^TEST_UI343"}})
        print("deleted tpl", r.deleted_count, "bit", b.deleted_count, "logs", e.deleted_count)
    c.close()

asyncio.run(main(sys.argv[1]))
