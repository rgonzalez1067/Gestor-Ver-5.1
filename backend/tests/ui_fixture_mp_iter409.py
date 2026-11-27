# UI fixture for Multiproyectos (iter 409). usage: python ui_fixture_mp_iter409.py create|cleanup
import sys
import json
from mp_fixture_iter409 import make_set, cleanup

F = "/tmp/mp_ui_iter409.json"
if sys.argv[1] == "create":
    d = make_set("UI")
    A = d["_client"]("A", "TEST_MARCA_UIA")
    B = d["_client"]("B", "TEST_MARCA_UIB")
    qa = d["_quote"](A, "Aprobada", "qa", minutes=0)
    qb = d["_quote"](B, "Pagada", "qb", minutes=1)
    qc = d["_quote"](B, "Facturada", "qc", minutes=2)
    d["_serials"](qa, A, 2)
    d["_serials"](qb, B, 3)
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    out.update(qa=qa, qb=qb, qc=qc, A=A, B=B)
    json.dump(out, open(F, "w"))
    print(json.dumps(out))
else:
    d = json.load(open(F))
    cleanup(d)
    print("cleaned")
