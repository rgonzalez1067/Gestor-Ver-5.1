# Fixture helper for Multiproyectos tests (iter 409): creates/cleans TEST_ clients, quotes, serial_assignments
import os
import uuid
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

_db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]


def db():
    return _db


def make_set(tag: str):
    """Returns dict with ids. tag used in names."""
    u = uuid.uuid4().hex[:6]
    grp = f"TEST_GRP_{tag}_{u}"
    base = datetime.now(timezone.utc) - timedelta(days=1)
    ids = {"clients": [], "quotes": [], "serials": [], "grupo": grp}

    def client(suffix, marca):
        cid = f"cli_test_{tag}_{suffix}_{u}"
        _db.clients.insert_one({"client_id": cid, "rif": f"J9{u}{suffix}", "legal_name": f"TEST_Cliente {tag} {suffix} {u}",
                                "fantasy_name": marca, "grupo_economico": grp, "sucursal": "Principal",
                                "email": f"test_{u}{suffix}@example.invalid", "created_at": base.isoformat()})
        ids["clients"].append(cid)
        return cid

    def quote(cid, status, n, extra=None, minutes=0):
        qid = f"quo_test_{tag}_{n}_{u}"
        doc = {"quote_id": qid, "quote_number": f"TEST-COT-{tag}-{n}-{u}", "client_id": cid, "client_name": "TEST",
               "quote_category": "implementation", "quote_type": "VPOS", "quote_status": status, "total_usd": 100,
               "services": [{"item_type": "additional", "bank_name": "TEST_Banco", "item_name": "TEST_Prod", "quantity": 1}],
               "sent_to_implementation_at": None, "client_segment": "PYME", "cantidad_cajas": 1,
               "created_at": (base + timedelta(minutes=minutes)).isoformat()}
        if extra:
            doc.update(extra)
        _db.quotes.insert_one(doc)
        ids["quotes"].append(qid)
        return qid

    def serials(qid, cid, count, status="preasignado"):
        out = []
        for i in range(count):
            aid = f"sa_test_{uuid.uuid4().hex[:10]}"
            _db.serial_assignments.insert_one({"assignment_id": aid, "serial": f"TESTSER{u}{qid[-8:]}{i}{status[:2]}",
                                               "item_name": "TEST_Morefun MP63", "warehouse_id": "whs_f00b02f4",
                                               "quote_id": qid, "client_id": cid, "status": status})
            ids["serials"].append(aid)
            out.append(aid)
        return out

    ids["_client"], ids["_quote"], ids["_serials"] = client, quote, serials
    return ids


def cleanup(ids, project_ids=()):
    qids = ids["quotes"]
    _db.quotes.delete_many({"quote_id": {"$in": qids}})
    _db.quote_history.delete_many({"quote_id": {"$in": qids}})
    _db.proyecto_cotizaciones.delete_many({"cotizacion_id": {"$in": qids}})
    _db.serial_assignments.delete_many({"assignment_id": {"$in": ids["serials"]}})
    _db.clients.delete_many({"client_id": {"$in": ids["clients"]}})
    pids = list(project_ids) + [p["project_id"] for p in _db.projects.find({"quote_id": {"$in": qids}}, {"project_id": 1})]
    if pids:
        _db.projects.delete_many({"project_id": {"$in": pids}})
        _db.proyecto_cotizaciones.delete_many({"proyecto_id": {"$in": pids}})
