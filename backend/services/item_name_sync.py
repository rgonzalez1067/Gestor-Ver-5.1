"""Mantiene el nombre de los ítems de inventario/seriales alineado con el catálogo (hardware)."""
import logging
from typing import Optional

from config import db

COLLECTIONS = ("inventory_movements", "serial_assignments")


async def sync_item_names(hardware_id: Optional[str] = None) -> int:
    query = {"hardware_id": hardware_id} if hardware_id else {}
    updated = 0
    async for hw in db.hardware.find(query, {"_id": 0, "hardware_id": 1, "name": 1}):
        name = (hw.get("name") or "").strip()
        if not name:
            continue
        for col in COLLECTIONS:
            r = await db[col].update_many({"item_id": hw["hardware_id"], "item_name": {"$ne": name}}, {"$set": {"item_name": name}})
            updated += r.modified_count
    if updated:
        logging.info(f"[item_name_sync] {updated} registros actualizados")
    return updated
