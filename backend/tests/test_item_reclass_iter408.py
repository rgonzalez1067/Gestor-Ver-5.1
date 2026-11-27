# Admin internal reclass (product -> product, same warehouse) — iteration 408
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"}
NONADMIN = {"email": "kherrera@megasoft.com.ve", "password": "Kherrera2026*Qa"}
TAG = uuid.uuid4().hex[:6]


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        return None
    tok = r.json().get("session_token") or r.json().get("token")
    if not tok:
        return None
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def ctx():
    s = _login(ADMIN)
    if not s:
        pytest.skip("admin login failed")
    c = {"s": s, "hw": [], "movs": [], "wh": None, "asg": []}
    wh = s.post(f"{BASE_URL}/api/inventory/warehouses", json={"name": f"TEST_RCL_WH_{TAG}", "location": "TEST", "notes": "TEST"})
    assert wh.status_code == 200, wh.text
    c["wh"] = wh.json()["warehouse_id"]

    def mk(name, typ, marca=None):
        body = {"name": f"TEST_RCL_{name}_{TAG}", "type": typ, "price_usd": 10, "price_bs_usd": 10}
        if marca:
            body["marca"] = marca
        r = s.post(f"{BASE_URL}/api/hardware", json=body)
        assert r.status_code == 200, r.text
        c["hw"].append(r.json()["hardware_id"])
        return r.json()["hardware_id"]

    c["ns_a"] = mk("ACC_A", "Accesorio")
    c["ns_b"] = mk("ACC_B", "Accesorio")
    c["s_a"] = mk("POS_A", "POS", "Verifone")
    c["s_b"] = mk("POS_B", "POS", "Verifone")
    c["serials"] = [f"TESTRCL{TAG}{i}" for i in range(4)]

    for iid, qty, ser, cost in ((c["ns_a"], 10, [], 20), (c["ns_b"], 2, [], 30), (c["s_a"], 4, c["serials"], 50)):
        r = s.post(f"{BASE_URL}/api/inventory/warehouses/{c['wh']}/entry",
                   json={"item_id": iid, "quantity": qty, "unit_cost": cost, "serials": ser, "notes": "TEST entry"})
        assert r.status_code == 200, r.text
        c["movs"].append(r.json()["movement_id"])
        assert r.json().get("certification_status") == "certificado"
    yield c
    # cleanup — only ids we created
    for mid in c["movs"]:
        s.delete(f"{BASE_URL}/api/inventory/movements/{mid}")
    if c["asg"]:
        m = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
        m.serial_assignments.delete_many({"assignment_id": {"$in": c["asg"]}})
    s.delete(f"{BASE_URL}/api/inventory/warehouses/{c['wh']}")
    for h in c["hw"]:
        s.delete(f"{BASE_URL}/api/hardware/{h}")


def _stock(c, iid):
    r = c["s"].get(f"{BASE_URL}/api/inventory/warehouses/{c['wh']}/stock")
    assert r.status_code == 200
    return next((x for x in r.json() if x["item_id"] == iid), None)


def _post(c, **kw):
    body = {"warehouse_id": c["wh"], "notes": "TEST duplicado por nombre"}
    body.update(kw)
    r = c["s"].post(f"{BASE_URL}/api/admin/inventory/item-reclass", json=body)
    if r.status_code == 200:
        c["movs"].extend(m["movement_id"] for m in r.json()["movements"])
    return r


# --- targets ---
def test_targets_non_serialized(ctx):
    r = ctx["s"].get(f"{BASE_URL}/api/admin/inventory/reclass-targets", params={"item_id": ctx["ns_a"]})
    assert r.status_code == 200
    d = r.json()
    assert d["requires_serial"] is False
    ids = {i["item_id"] for i in d["items"]}
    assert ctx["ns_b"] in ids and ctx["ns_a"] not in ids and ctx["s_b"] not in ids


def test_targets_serialized(ctx):
    r = ctx["s"].get(f"{BASE_URL}/api/admin/inventory/reclass-targets", params={"item_id": ctx["s_a"]})
    d = r.json()
    assert d["requires_serial"] is True
    ids = {i["item_id"] for i in d["items"]}
    assert ctx["s_b"] in ids and ctx["s_a"] not in ids and ctx["ns_b"] not in ids
    assert all(i["type"].lower() in ("pos", "pinpad", "mpos") for i in d["items"])


def test_targets_404(ctx):
    r = ctx["s"].get(f"{BASE_URL}/api/admin/inventory/reclass-targets", params={"item_id": "hwr_nope_xx"})
    assert r.status_code == 404


def test_non_admin_403(ctx):
    # temp TEST_ non-admin user + session inserted directly (avoids lockout of real accounts)
    from datetime import datetime, timezone, timedelta
    m = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
    uid, tok = f"user_TEST_{TAG}", f"tok_TEST_{uuid.uuid4().hex}"
    m.users.insert_one({"user_id": uid, "email": f"test_rcl_{TAG}@example.com", "first_name": "TEST_", "last_name": "RCL", "role": "user"})
    m.user_sessions.insert_one({"user_id": uid, "session_token": tok, "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    try:
        _non_admin_checks(ctx, s)
    finally:
        m.users.delete_one({"user_id": uid})
        m.user_sessions.delete_one({"session_token": tok})


def _non_admin_checks(ctx, s):
    r = s.get(f"{BASE_URL}/api/admin/inventory/reclass-targets", params={"item_id": ctx["ns_a"]})
    assert r.status_code == 403
    r = s.post(f"{BASE_URL}/api/admin/inventory/item-reclass", json={"warehouse_id": ctx["wh"], "source_item_id": ctx["ns_a"], "dest_item_id": ctx["ns_b"], "quantity": 1, "notes": "TEST hack"})
    assert r.status_code == 403


def test_no_auth_401(ctx):
    r = requests.post(f"{BASE_URL}/api/admin/inventory/item-reclass", json={})
    assert r.status_code in (401, 403)


# --- validations ---
@pytest.mark.parametrize("kw,frag", [
    ({"source_item_id": "SAME", "dest_item_id": "SAME", "quantity": 1}, "distintos"),
    ({"quantity": 1, "notes": "abc"}, "motivo"),
    ({"quantity": 11}, "insuficiente"),
    ({"quantity": 0}, "Faltan"),
])
def test_validations_non_serial(ctx, kw, frag):
    kw = dict(kw)
    if kw.get("source_item_id") == "SAME":
        kw["source_item_id"] = kw["dest_item_id"] = ctx["ns_a"]
    kw.setdefault("source_item_id", ctx["ns_a"])
    kw.setdefault("dest_item_id", ctx["ns_b"])
    r = _post(ctx, **kw)
    assert r.status_code == 400, r.text
    assert frag.lower() in r.json()["detail"].lower()


def test_mismatch_serial_type(ctx):
    r = _post(ctx, source_item_id=ctx["ns_a"], dest_item_id=ctx["s_b"], quantity=1)
    assert r.status_code == 400 and "serial" in r.json()["detail"].lower()


def test_serial_count_mismatch(ctx):
    r = _post(ctx, source_item_id=ctx["s_a"], dest_item_id=ctx["s_b"], quantity=2, serials=[ctx["serials"][0]])
    assert r.status_code == 400 and "exactamente" in r.json()["detail"]


def test_serial_not_in_stock(ctx):
    r = _post(ctx, source_item_id=ctx["s_a"], dest_item_id=ctx["s_b"], quantity=1, serials=["TESTRCL_NOPE"])
    assert r.status_code == 400 and "no disponibles" in r.json()["detail"]


def test_serial_duplicate_in_list(ctx):
    r = _post(ctx, source_item_id=ctx["s_a"], dest_item_id=ctx["s_b"], quantity=2, serials=[ctx["serials"][0]] * 2)
    assert r.status_code == 400


def test_preassigned_serial_blocked(ctx):
    m = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
    aid = f"sa_TEST_{TAG}"
    m.serial_assignments.insert_one({"assignment_id": aid, "serial": ctx["serials"][3], "status": "preasignado", "item_id": ctx["s_a"], "warehouse_id": ctx["wh"]})
    ctx["asg"].append(aid)
    r = _post(ctx, source_item_id=ctx["s_a"], dest_item_id=ctx["s_b"], quantity=1, serials=[ctx["serials"][3]])
    assert r.status_code == 400 and "preasignados" in r.json()["detail"], r.text


def test_bad_warehouse_404(ctx):
    r = ctx["s"].post(f"{BASE_URL}/api/admin/inventory/item-reclass", json={"warehouse_id": "wh_nope", "source_item_id": ctx["ns_a"], "dest_item_id": ctx["ns_b"], "quantity": 1, "notes": "TEST motivo"})
    assert r.status_code == 404


def test_non_numeric_quantity(ctx):
    r = _post(ctx, source_item_id=ctx["ns_a"], dest_item_id=ctx["ns_b"], quantity="abc")
    assert r.status_code in (400, 422), f"got {r.status_code}"


# --- happy paths ---
def test_non_serial_reclass(ctx):
    r = _post(ctx, source_item_id=ctx["ns_a"], dest_item_id=ctx["ns_b"], quantity=3)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["quantity"] == 3 and d["serials"] == [] and d["reclass_id"].startswith("rcl_")
    assert len(d["movements"]) == 2
    assert all(m["unit_cost"] == 20 and m.get("internal_reclass") for m in d["movements"])
    a, b = _stock(ctx, ctx["ns_a"]), _stock(ctx, ctx["ns_b"])
    assert a["quantity"] == 7 and b["quantity"] == 5
    # weighted cost of dest: (2*30 + 3*20)/5 = 24
    assert b["weighted_cost"] == 24.0
    assert a["weighted_cost"] == 20.0


def test_serial_reclass(ctx):
    sel = ctx["serials"][:2]
    r = _post(ctx, source_item_id=ctx["s_a"], dest_item_id=ctx["s_b"], quantity=2, serials=sel)
    assert r.status_code == 200, r.text
    assert sorted(r.json()["serials"]) == sorted(sel)
    a, b = _stock(ctx, ctx["s_a"]), _stock(ctx, ctx["s_b"])
    assert a["quantity"] == 2 and b["quantity"] == 2
    assert sorted(b["serials"]) == sorted(sel)
    assert not set(sel) & set(a["serials"])
    assert ctx["serials"][2] in a["serials"]
    assert b["weighted_cost"] == 50.0
    # moved serial cannot be moved again from source
    r2 = _post(ctx, source_item_id=ctx["s_a"], dest_item_id=ctx["s_b"], quantity=1, serials=[sel[0]])
    assert r2.status_code == 400


def test_kardex(ctx):
    k = ctx["s"].get(f"{BASE_URL}/api/inventory/warehouses/{ctx['wh']}/kardex/{ctx['ns_a']}").json()
    out = [m for m in k["movements"] if m["movement_type"] == "transferencia_salida"]
    assert out and "Transferencia interna" in out[-1]["reference"]
    assert k["saldo_final"] == 7
    k2 = ctx["s"].get(f"{BASE_URL}/api/inventory/warehouses/{ctx['wh']}/kardex/{ctx['ns_b']}").json()
    inn = [m for m in k2["movements"] if m["movement_type"] == "transferencia_entrada"]
    assert inn and "Transferencia interna desde" in inn[-1]["reference"]
    assert k2["saldo_final"] == 5
    ks = ctx["s"].get(f"{BASE_URL}/api/inventory/warehouses/{ctx['wh']}/kardex/{ctx['s_b']}").json()
    assert ks["saldo_final"] == 2


def test_kardex_exposes_internal_reclass_flag(ctx):
    k = ctx["s"].get(f"{BASE_URL}/api/inventory/warehouses/{ctx['wh']}/kardex/{ctx['ns_b']}").json()
    inn = [m for m in k["movements"] if m["movement_type"] == "transferencia_entrada"]
    assert inn[-1].get("internal_reclass") is True, "kardex does not expose internal_reclass"
