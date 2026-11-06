"""Rebranding idempotente en BD: 'MegaNexus' → 'Gestor - CRM' en plantillas/configuración visibles."""
import re

COLLS = ["email_templates", "config", "action_notification_configs", "other_action_configs", "message_templates",
         "notification_config", "project_sla_action_configs", "corporate_anexos", "cc_groups"]


def _fix(v):
    if isinstance(v, str):
        for a in ("Gestor MegaNexus", "MegaNexus Gestor", "Gestor | MegaNexus"):
            v = v.replace(a, "Gestor - CRM")
        return re.sub(r"MegaNexus", "Gestor - CRM", v)
    if isinstance(v, dict):
        return {k: _fix(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_fix(x) for x in v]
    return v


async def rebrand_db(db) -> int:
    changed = 0
    for c in COLLS:
        async for d in db[c].find({}):
            nd = _fix(d)
            if nd != d:
                await db[c].replace_one({"_id": d["_id"]}, nd)
                changed += 1
    return changed
