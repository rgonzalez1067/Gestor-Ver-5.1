# Referentes catalog (master) + Initial Contacts integration (referente_id / nuevo_referente) + RBAC + audit
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = ("qa.integradores@megasoft.com.ve", "QaIntegr2026*Ok")
NONADMIN = ("qa.editor@megasoft.com.ve", "QaIntegr2026*Ok")
SUF = uuid.uuid4().hex[:6]

CREATED_CONTACTS, CREATED_REFS = [], []


def _login(email, pwd):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200 or "session_token" not in r.json():
        pytest.skip(f"login failed {email}: {r.status_code}")
    s.headers.update({"Authorization": f"Bearer {r.json()['session_token']}"})
    s.user = r.json()["user"]
    return s


@pytest.fixture(scope="module")
def admin():
    s = _login(*ADMIN)
    yield s
    for cid in CREATED_CONTACTS:
        s.delete(f"{BASE_URL}/api/initial-contacts/{cid}")
    for rid in CREATED_REFS:
        s.put(f"{BASE_URL}/api/referentes/{rid}", json={"estatus": False})


@pytest.fixture(scope="module")
def editor():
    return _login(*NONADMIN)


def _mk_ref(s, **kw):
    payload = {"nombre_referente": f"TEST_Ref_{SUF}_{uuid.uuid4().hex[:4]}", "tipo_referente": "PERSONA", **kw}
    r = s.post(f"{BASE_URL}/api/referentes", json=payload)
    assert r.status_code == 200, r.text
    CREATED_REFS.append(r.json()["referente_id"])
    return r.json()


def _mk_contact(s, **kw):
    payload = {"contact_name": f"TEST_Contact_{SUF}", "legal_name": f"TEST_Empresa_{SUF}",
               "assigned_to_user_id": s.user["user_id"], **kw}
    r = s.post(f"{BASE_URL}/api/initial-contacts", json=payload)
    return r


def _contact(s, cid):
    r = s.get(f"{BASE_URL}/api/initial-contacts/{cid}")
    if r.status_code == 200:
        return r.json()
    items = s.get(f"{BASE_URL}/api/initial-contacts").json()
    items = items if isinstance(items, list) else items.get("items", items.get("contacts", []))
    return next(c for c in items if c["contact_id"] == cid)


def _ids(s, **params):
    r = s.get(f"{BASE_URL}/api/referentes", params=params)
    assert r.status_code == 200
    return r


# --- GET list ---
def test_list_sorted_and_flags(admin):
    r = _ids(admin)
    d = r.json()
    assert d["can_create"] is True
    names = [x["nombre_referente"].casefold() for x in d["items"]]
    assert names == sorted(names)
    assert all(x["estatus"] for x in d["items"])
    assert all("contactos" in x and "nombre_norm" not in x for x in d["items"])
    ccm = [x for x in d["items"] if x["nombre_referente"] == "CCM"]
    assert ccm and ccm[0]["contactos"] >= 1


# --- create with optional fields + duplicate 409 ---
def test_create_minimal_and_full_and_dup(admin):
    a = _mk_ref(admin)
    assert a["empresa"] == "" and a["persona"] == "" and a["estatus"] is True and a["fecha_creacion"]
    b = _mk_ref(admin, tipo_referente="EMPRESA", empresa="TEST_Emp", persona="TEST_Per")
    assert b["tipo_referente"] == "EMPRESA" and b["empresa"] == "TEST_Emp"
    dup = admin.post(f"{BASE_URL}/api/referentes", json={"nombre_referente": a["nombre_referente"].upper(), "tipo_referente": "AREA"})
    assert dup.status_code == 409
    ids = [x["referente_id"] for x in _ids(admin).json()["items"]]
    assert a["referente_id"] in ids and b["referente_id"] in ids


def test_create_validation(admin):
    r = admin.post(f"{BASE_URL}/api/referentes", json={"nombre_referente": "x" * 151, "tipo_referente": "PERSONA"})
    assert r.status_code == 422
    r = admin.post(f"{BASE_URL}/api/referentes", json={"nombre_referente": "TEST_bad", "tipo_referente": "OTRO"})
    assert r.status_code == 422


# --- PUT / inactivate / rename propagation ---
def test_update_inactivate_and_rename(admin):
    ref = _mk_ref(admin)
    c = _mk_contact(admin, referente_id=ref["referente_id"])
    assert c.status_code == 200, c.text
    cid = c.json()["contact_id"]
    CREATED_CONTACTS.append(cid)
    assert c.json()["referente_id"] == ref["referente_id"]
    new_name = f"TEST_Renamed_{SUF}"
    u = admin.put(f"{BASE_URL}/api/referentes/{ref['referente_id']}", json={"nombre_referente": new_name, "empresa": "TEST_E2"})
    assert u.status_code == 200 and u.json()["nombre_referente"] == new_name and u.json()["empresa"] == "TEST_E2"
    assert _contact(admin, cid)["referred_by"] == new_name
    u = admin.put(f"{BASE_URL}/api/referentes/{ref['referente_id']}", json={"estatus": False})
    assert u.status_code == 200 and u.json()["estatus"] is False
    assert ref["referente_id"] not in [x["referente_id"] for x in _ids(admin).json()["items"]]
    inc = [x for x in _ids(admin, include_inactive="true").json()["items"] if x["referente_id"] == ref["referente_id"]]
    assert inc and inc[0]["estatus"] is False and inc[0]["contactos"] == 1


def test_update_404(admin):
    assert admin.put(f"{BASE_URL}/api/referentes/ref_nope", json={"estatus": False}).status_code == 404


# --- merge ---
def test_merge(admin):
    t = _mk_ref(admin)
    s1 = _mk_ref(admin)
    c = _mk_contact(admin, referente_id=s1["referente_id"])
    assert c.status_code == 200
    cid = c.json()["contact_id"]
    CREATED_CONTACTS.append(cid)
    m = admin.post(f"{BASE_URL}/api/referentes/merge", json={"target_id": t["referente_id"], "source_ids": [s1["referente_id"]]})
    assert m.status_code == 200, m.text
    assert m.json()["contactos_reasignados"] == 1 and m.json()["referentes_fusionados"] == 1
    cc = _contact(admin, cid)
    assert cc["referente_id"] == t["referente_id"] and cc["referred_by"] == t["nombre_referente"]
    inc_ids = [x["referente_id"] for x in _ids(admin, include_inactive="true").json()["items"]]
    assert s1["referente_id"] not in inc_ids and t["referente_id"] in inc_ids
    # merged name can be reused
    assert admin.post(f"{BASE_URL}/api/referentes/merge", json={"target_id": t["referente_id"], "source_ids": [t["referente_id"]]}).status_code == 400


# --- initial contact with nuevo_referente ---
def test_contact_nuevo_referente_and_reuse(admin):
    name = f"TEST_Quick_{SUF}"
    r = _mk_contact(admin, nuevo_referente={"nombre_referente": name, "tipo_referente": "EMPRESA", "empresa": "TEST_QE", "persona": "TEST_QP"})
    assert r.status_code == 200, r.text
    CREATED_CONTACTS.append(r.json()["contact_id"])
    rid = r.json()["referente_id"]
    assert rid and r.json()["referred_by"] == name
    CREATED_REFS.append(rid)
    items = _ids(admin).json()["items"]
    ref = next(x for x in items if x["referente_id"] == rid)
    assert ref["tipo_referente"] == "EMPRESA" and ref["empresa"] == "TEST_QE" and ref["contactos"] == 1
    r2 = _mk_contact(admin, nuevo_referente={"nombre_referente": name.lower(), "tipo_referente": "PERSONA"})
    assert r2.status_code == 200
    CREATED_CONTACTS.append(r2.json()["contact_id"])
    assert r2.json()["referente_id"] == rid
    assert len([x for x in _ids(admin).json()["items"] if x["nombre_referente"].casefold() == name.casefold()]) == 1


def test_contact_invalid_referente_id(admin):
    r = _mk_contact(admin, referente_id="ref_doesnotexist")
    assert r.status_code == 400


# --- audit ---
def test_audit_create_referente(admin):
    ref = _mk_ref(admin)
    import time
    time.sleep(2)
    r = admin.get(f"{BASE_URL}/api/audit-trails", params={"modules": "Referentes", "action": "CREATE", "page_size": 50})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    blob = str(items)
    assert ref["nombre_referente"] in blob or ref["referente_id"] in blob, items[:2]


# --- RBAC ---
def test_nonadmin_rbac(admin, editor):
    g = editor.get(f"{BASE_URL}/api/referentes")
    assert g.status_code == 200 and g.json()["can_create"] is False
    assert editor.post(f"{BASE_URL}/api/referentes", json={"nombre_referente": f"TEST_NoPerm_{SUF}", "tipo_referente": "PERSONA"}).status_code == 403
    ref = _mk_ref(admin)
    assert editor.put(f"{BASE_URL}/api/referentes/{ref['referente_id']}", json={"estatus": False}).status_code == 403
    assert editor.post(f"{BASE_URL}/api/referentes/merge", json={"target_id": ref["referente_id"], "source_ids": ["x"]}).status_code == 403
    gi = editor.get(f"{BASE_URL}/api/referentes", params={"include_inactive": "true"}).json()["items"]
    assert all(x["estatus"] for x in gi)
    r = _mk_contact(editor, nuevo_referente={"nombre_referente": f"TEST_NoPerm2_{SUF}", "tipo_referente": "PERSONA"})
    if r.status_code == 200:
        CREATED_CONTACTS.append(r.json()["contact_id"])
    assert r.status_code == 403, r.text
    print("editor nuevo_referente detail:", r.json())
