# UI fixture for Multiproyectos per-quote summaries (iter 410). usage: python ui_fixture_mp_iter410.py create|cleanup
import sys
import json
from mp_fixture_iter409 import make_set, cleanup, db

F = "/tmp/mp_ui_iter410.json"
if sys.argv[1] == "create":
    d = make_set("U410")
    A = d["_client"]("A", "TEST_MARCA_U410A")
    B = d["_client"]("B", "TEST_MARCA_U410B")
    qa = d["_quote"](A, "Aprobada", "qa", {"services": [{"item_type": "additional", "bank_name": "Banco X", "item_name": "Prod A", "quantity": 2}]}, minutes=0)
    qb = d["_quote"](B, "Aprobada", "qb", {"services": [{"item_type": "additional", "bank_name": "Banco Y", "item_name": "Prod B", "quantity": 3}]}, minutes=1)
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    out.update(qa=qa, qb=qb, A=A, B=B)
    json.dump(out, open(F, "w"))
    print(json.dumps(out))
else:
    d = json.load(open(F))
    pids = [p["project_id"] for p in db().proyecto_cotizaciones.find({"cotizacion_id": {"$in": d["quotes"]}}, {"proyecto_id": 1, "project_id": 1}) if p.get("project_id")]
    pids += [p["proyecto_id"] for p in db().proyecto_cotizaciones.find({"cotizacion_id": {"$in": d["quotes"]}})]
    cleanup(d, pids)
    print("cleaned", pids)
