# In-process read-only check: followup report rows == Projects grid visibility for non-admin users (Implementador, Ventas).
import asyncio
import sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")


async def main():
    from config import db
    from routes.projects import _build_project_visibility_query
    from routes.projects_followup_report import _rows
    users = await db.users.find({"role": {"$ne": "admin"}, "$or": [{"cargo": "Implementador"}, {"email": "kherrera@megasoft.com.ve"},
                                {"departamento": {"$regex": "ventas", "$options": "i"}}]},
                                {"_id": 0, "password_hash": 0}).to_list(50)
    for u in users[:12]:
        q = await _build_project_visibility_query(u)
        grid = {p["project_id"] for p in await db.projects.find(q, {"_id": 0, "project_id": 1}).to_list(5000)}
        rows, kpis, _ = await _rows(u, "", "", "", "", "", "")
        rep = {r["project_id"] for r in rows}
        impl_ok = all(r["implementador"] == u.get("name") or u.get("cargo") != "Implementador" for r in rows)
        print(u.get("email"), u.get("cargo"), u.get("departamento"), "grid", len(grid), "report", len(rep),
              "EQUAL" if grid == rep else "DIFF", "impl_only_own" if impl_ok else "IMPL_MISMATCH")

asyncio.run(main())
