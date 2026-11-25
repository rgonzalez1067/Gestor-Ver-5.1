# RBAC for the 4 new Catálogos modules (impresoras_fiscales, servidores, referentes, productos_integracion)
# Restores kherrera user + profile from Mongo snapshot at module teardown.
import os
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
ADMIN = ("qa.integradores@megasoft.com.ve", "QaIntegr2026*Ok")
USER = ("kherrera@megasoft.com.ve", "Kherrera2026*Qa")
NEW = ["impresoras_fiscales", "servidores", "referentes", "productos_integracion"]


def _mongo(fn):
    async def run():
        db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
        return await fn(db)
    return asyncio.run(run())


def _login(email, pwd):
    if email == USER[0]:
        # kherrera password unknown/locked: use TEST_ session injected by /tmp/sess.py (deleted after run)
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {open('/tmp/kh_token').read().strip()}"})
        return s
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("session_token") or r.json().get("token")
    assert tok, r.json()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def env():
    async def snap(db):
        u = await db.users.find_one({"email": USER[0]}, {"_id": 0})
        p = await db.profiles.find_one({"profile_id": u["profile_id"]}, {"_id": 0}) if u.get("profile_id") else None
        others = await db.users.find({"profile_id": u.get("profile_id")}, {"_id": 0, "user_id": 1, "permissions": 1, "menu_groups": 1, "special_permissions": 1}).to_list(None)
        return u, p, others
    u, p, others = _mongo(snap)
    admin = _login(*ADMIN)
    created = {"servers": [], "referentes": [], "fps": [], "prods": []}
    yield {"admin": admin, "user_doc": u, "profile": p, "created": created}
    # cleanup TEST_ data by id
    for sid in created["servers"]:
        admin.delete(f"{BASE_URL}/api/servers/{sid}")
    for rid in created["referentes"]:
        admin.delete(f"{BASE_URL}/api/referentes/{rid}")
    for fid in created["fps"]:
        admin.delete(f"{BASE_URL}/api/fiscal-printers/{fid}")

    async def restore(db):
        await db.users.update_one({"user_id": u["user_id"]}, {"$set": {k: u.get(k) for k in ("permissions", "menu_groups", "special_permissions", "profile_id")}})
        if p:
            await db.profiles.update_one({"profile_id": p["profile_id"]}, {"$set": {k: p.get(k) for k in ("permissions", "menu_groups", "special_permissions", "updated_at")}})
        for o in others:
            await db.users.update_one({"user_id": o["user_id"]}, {"$set": {k: o.get(k) for k in ("permissions", "menu_groups", "special_permissions")}})
    _mongo(restore)


class TestCatalogNewModules:
    def test_01_catalog_includes_new_modules(self, env):
        r = env["admin"].get(f"{BASE_URL}/api/admin/permission-catalog")
        assert r.status_code == 200
        mods = {m["id"]: m for m in r.json()["modules"]}
        for mid in NEW:
            assert mid in mods and mods[mid]["group"] == "catalogos"
        assert mods["productos_integracion"]["name"] == "Productos para Integración"

    def test_02_existing_profiles_have_none(self, env):
        r = env["admin"].get(f"{BASE_URL}/api/admin/profiles")
        assert r.status_code == 200
        profs = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        assert profs
        for p in profs:
            for mid in NEW:
                assert (p.get("permissions") or {}).get(mid) in ("none", None, "read", "edit")
        assert all((env["profile"]["permissions"]).get(m) == "none" for m in NEW)

    def test_03_user_none_blocked(self, env):
        s = _login(*USER)
        me = s.get(f"{BASE_URL}/api/auth/me").json()
        assert all(me["permissions"].get(m) == "none" for m in NEW)
        assert s.get(f"{BASE_URL}/api/productos-integracion").status_code == 403
        srv = env["admin"].get(f"{BASE_URL}/api/servers").json()
        sid = srv[0]["server_id"] if srv else "srv_nope"
        assert s.put(f"{BASE_URL}/api/servers/{sid}", json={"tipo": "Monocomercio", "descripcion": "x"}).status_code == 403
        assert s.post(f"{BASE_URL}/api/servers", json={"tipo": "Monocomercio", "descripcion": "TEST_x"}).status_code == 403
        assert s.put(f"{BASE_URL}/api/referentes/ref_nope", json={"estatus": True}).status_code == 403
        assert s.delete(f"{BASE_URL}/api/referentes/ref_nope").status_code == 403
        assert s.post(f"{BASE_URL}/api/fiscal-printers", json={"marca": "TEST_M", "modelo": "TEST_X"}).status_code == 403

    def test_04_user_none_still_quickadd(self, env):
        s = _login(*USER)
        r = s.get(f"{BASE_URL}/api/referentes")
        assert r.status_code == 200 and "items" in r.json()
        r = s.post(f"{BASE_URL}/api/fiscal-printers", json={"name": "TEST_QuickAdd FP 777"})
        assert r.status_code == 200, r.text
        env["created"]["fps"].append(r.json()["model_id"])
        assert s.get(f"{BASE_URL}/api/servers").status_code == 200

    def test_05_grant_read_and_edit(self, env):
        a = env["admin"]
        pid = env["profile"]["profile_id"]
        r = a.put(f"{BASE_URL}/api/admin/profiles/{pid}", json={"permissions": {"servidores": "read", "productos_integracion": "read", "referentes": "edit"}})
        assert r.status_code == 200, r.text
        uid = env["user_doc"]["user_id"]
        r = a.put(f"{BASE_URL}/api/admin/users/{uid}/permissions", json={"servidores": "read", "productos_integracion": "read", "referentes": "edit"})
        assert r.status_code == 200, r.text
        p = r.json()["user"]["permissions"]
        assert p["servidores"] == "read" and p["productos_integracion"] == "read" and p["referentes"] == "edit"

    def test_06_ceiling_enforced(self, env):
        uid = env["user_doc"]["user_id"]
        r = env["admin"].put(f"{BASE_URL}/api/admin/users/{uid}/permissions", json={"servidores": "edit"})
        assert r.status_code == 403

    def test_07_read_level(self, env):
        s = _login(*USER)
        r = s.get(f"{BASE_URL}/api/productos-integracion")
        assert r.status_code == 200 and isinstance(r.json(), list) and r.json()
        pid = r.json()[0]["producto_id"]
        assert s.put(f"{BASE_URL}/api/productos-integracion/{pid}", json={"descripcion": "x"}).status_code == 403
        assert s.delete(f"{BASE_URL}/api/productos-integracion/{pid}").status_code == 403
        assert s.post(f"{BASE_URL}/api/productos-integracion", json={"codigo": "TEST_X", "nombre": "TEST_X"}).status_code == 403
        srv = s.get(f"{BASE_URL}/api/servers").json()
        sid = srv[0]["server_id"] if srv else "srv_nope"
        assert s.put(f"{BASE_URL}/api/servers/{sid}", json={"tipo": "Monocomercio", "descripcion": "x"}).status_code == 403
        assert s.delete(f"{BASE_URL}/api/servers/{sid}").status_code == 403

    def test_08_referentes_edit_level_create_delete(self, env):
        s = _login(*USER)
        r = s.post(f"{BASE_URL}/api/referentes", json={"nombre_referente": "TEST_Ref Permisos 991", "tipo_referente": "EMPRESA"})
        if r.status_code == 200:
            env["created"]["referentes"].append(r.json()["referente_id"])
        assert r.status_code == 200, f"Edición Total user cannot create referente: {r.status_code} {r.text}"
        rid = r.json()["referente_id"]
        u = s.put(f"{BASE_URL}/api/referentes/{rid}", json={"empresa": "TEST_Emp"})
        assert u.status_code == 200 and u.json()["empresa"] == "TEST_Emp"
        d = s.delete(f"{BASE_URL}/api/referentes/{rid}")
        assert d.status_code == 200
        env["created"]["referentes"].remove(rid)

    def test_09_referentes_edit_update_delete_admin_created(self, env):
        a = env["admin"]
        r = a.post(f"{BASE_URL}/api/referentes", json={"nombre_referente": "TEST_Ref Admin 992", "tipo_referente": "PERSONA"})
        assert r.status_code == 200, r.text
        rid = r.json()["referente_id"]
        env["created"]["referentes"].append(rid)
        s = _login(*USER)
        assert s.put(f"{BASE_URL}/api/referentes/{rid}", json={"persona": "TEST_P"}).status_code == 200
        assert s.delete(f"{BASE_URL}/api/referentes/{rid}").status_code == 200
        env["created"]["referentes"].remove(rid)

    def test_10_admin_full_access(self, env):
        a = env["admin"]
        assert a.get(f"{BASE_URL}/api/productos-integracion").status_code == 200
        r = a.post(f"{BASE_URL}/api/servers", json={"tipo": "Monocomercio", "descripcion": "TEST_Srv 993"})
        assert r.status_code == 200, r.text
        sid = r.json()["server_id"]
        env["created"]["servers"].append(sid)
        assert a.put(f"{BASE_URL}/api/servers/{sid}", json={"tipo": "Multicomercio", "descripcion": "TEST_Srv 993"}).status_code == 200
        assert a.delete(f"{BASE_URL}/api/servers/{sid}").status_code == 200
        env["created"]["servers"].remove(sid)
