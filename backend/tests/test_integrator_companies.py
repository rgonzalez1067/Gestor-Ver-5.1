# Empresas Integradoras (padre) -> Aplicativos (hijos) + técnicos de proyecto - regresión iter385
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"}
SUF = uuid.uuid4().hex[:6]
RND = str(uuid.uuid4().int)[:7]

STATE = {"companies": [], "integrators": []}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200 or not r.json().get("session_token"):
        return None
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def s():
    tok = _login(ADMIN)
    if not tok:
        pytest.skip("login failed")
    ses = requests.Session()
    ses.headers.update({"Authorization": f"Bearer {tok}"})
    yield ses
    # cleanup: integrators first, then companies (only the ones we created)
    for iid in STATE["integrators"]:
        ses.delete(f"{API}/integrators/{iid}")
    for eid in STATE["companies"]:
        ses.delete(f"{API}/integrator-companies/{eid}")


def payload(tipo="Jurídica", razon=None, rif=None, contacts=None, direccion="Av. QA, Caracas"):
    return {"tipo_persona": tipo, "razon_social": razon or f"QA Empresa Juridica {SUF}",
            "rif": rif or f"J{RND}1{0}", "direccion_fiscal": direccion,
            "contacts": contacts if contacts is not None else [
                {"full_name": "QA Ana", "phone": "0414-0000000", "email": "qa.ana@example.com", "role": "Gerente"},
                {"full_name": "QA Luis", "phone": "0412-0000000", "email": "qa.luis@example.com", "role": "Comercial"}]}


# --- Listado ---
def test_list_companies(s):
    r = s.get(f"{API}/integrator-companies")
    assert r.status_code == 200
    data = r.json()
    assert 300 <= len(data) <= 450, len(data)
    names = [d["razon_social"].lower() for d in data]
    assert names == sorted(names)
    for k in ("apps", "app_count", "ficha_incompleta", "principal_contact", "empresa_id"):
        assert k in data[0]
    assert "_id" not in data[0] and "norm_name" not in data[0]
    assert sum(d["app_count"] for d in data) > 400
    STATE["n_companies"] = len(data)
    print("companies:", len(data), "incomplete:", sum(d["ficha_incompleta"] for d in data))


def test_all_integrators_linked(s):
    r = s.get(f"{API}/integrators")
    assert r.status_code == 200
    rows = r.json()
    orphans = [x["integrator_id"] for x in rows if not x.get("empresa_integradora_id")]
    print("integrators:", len(rows), "orphans:", len(orphans))
    assert not orphans


# --- Validaciones POST ---
@pytest.mark.parametrize("body,code", [
    (dict(tipo="Natural", rif="J301122334"), 400),
    (dict(tipo="Jurídica", rif="V123456789"), 400),
    (dict(rif="J-3011-22"), 400),
    (dict(direccion="   "), 400),
    (dict(contacts=[]), 400),
    (dict(contacts=[{"full_name": "  "}]), 400),
    (dict(contacts=[{"full_name": "QA X", "email": "bad"}]), 400),
])
def test_create_validation(s, body, code):
    r = s.post(f"{API}/integrator-companies", json=payload(**body))
    assert r.status_code == code, r.text
    assert "detail" in r.json()


def test_create_juridica_normalizes_rif(s):
    raw = f"j{RND}12"  # j + 8 digits + 1 check
    raw = f"j{RND}1" + "2"
    r = s.post(f"{API}/integrator-companies", json=payload(rif=raw))
    assert r.status_code == 200, r.text
    d = r.json()
    STATE["companies"].append(d["empresa_id"])
    STATE["jur"] = d
    assert d["rif"] == f"J-{RND}1-2"
    assert d["ficha_incompleta"] is False and d["app_count"] == 0
    assert len(d["contacts"]) == 2 and d["principal_contact"] == "QA Ana"
    g = s.get(f"{API}/integrator-companies/{d['empresa_id']}")
    assert g.status_code == 200 and g.json()["razon_social"] == f"QA Empresa Juridica {SUF}"


def test_create_natural(s):
    r = s.post(f"{API}/integrator-companies", json=payload(tipo="Natural", razon=f"QA Persona Natural {SUF}", rif=f"V-{RND}2-3"))
    assert r.status_code == 200, r.text
    STATE["companies"].append(r.json()["empresa_id"])
    STATE["nat"] = r.json()
    assert r.json()["tipo_persona"] == "Natural"


def test_duplicates_409(s):
    r = s.post(f"{API}/integrator-companies", json=payload(razon=f"QA Otra {SUF}", rif=f"J-{RND}1-2"))
    assert r.status_code == 409
    # razón social variante (C.A.) también debe chocar
    r = s.post(f"{API}/integrator-companies", json=payload(razon=f"QA Empresa Juridica {SUF}, C.A.", rif=f"J-{RND}9-9"))
    assert r.status_code == 409


# --- RIF document ---
def test_rif_document(s):
    eid = STATE["jur"]["empresa_id"]
    bad = s.post(f"{API}/integrator-companies/{eid}/rif-document", files={"file": ("x.txt", b"hello", "text/plain")})
    assert bad.status_code == 400
    pdf = b"%PDF-1.4\n%QA\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    up = s.post(f"{API}/integrator-companies/{eid}/rif-document", files={"file": ("rif_qa.pdf", pdf, "application/pdf")})
    assert up.status_code == 200, up.text
    assert up.json()["rif_document_filename"] == "rif_qa.pdf"
    dl = s.get(f"{API}/integrator-companies/{eid}/rif-document")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("application/pdf")
    assert dl.content == pdf
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 30
    up2 = s.post(f"{API}/integrator-companies/{STATE['nat']['empresa_id']}/rif-document", files={"file": ("rif.png", png, "image/png")})
    assert up2.status_code == 200
    dl2 = s.get(f"{API}/integrator-companies/{STATE['nat']['empresa_id']}/rif-document")
    assert dl2.headers["content-type"].startswith("image/png")


def test_rif_document_missing_404(s):
    r = s.post(f"{API}/integrator-companies", json=payload(razon=f"QA SinDoc {SUF}", rif=f"G-{RND}3-4"))
    assert r.status_code == 200
    STATE["companies"].append(r.json()["empresa_id"])
    assert s.get(f"{API}/integrator-companies/{r.json()['empresa_id']}/rif-document").status_code == 404


# --- Integrators (hijos) ---
def test_create_integrator_with_company(s):
    eid = STATE["jur"]["empresa_id"]
    r = s.post(f"{API}/integrators", json={"name": "ignored name", "integrator_type": "Integrador", "app_name": f"QA App1 {SUF}",
                                             "integration_type": "API", "empresa_integradora_id": eid})
    assert r.status_code == 200, r.text
    d = r.json()
    STATE["integrators"].append(d["integrator_id"])
    STATE["app1"] = d["integrator_id"]
    assert d["name"] == STATE["jur"]["razon_social"]
    assert d["empresa_integradora_id"] == eid
    c = s.get(f"{API}/integrator-companies/{eid}").json()
    assert c["app_count"] == 1


def test_create_integrator_auto_company(s):
    nm = f"QA Auto Integrador {SUF}, C.A."
    r = s.post(f"{API}/integrators", json={"name": nm, "integrator_type": "Integrador", "app_name": f"QA AutoApp {SUF}",
                                             "integration_type": "API"})
    assert r.status_code == 200, r.text
    d = r.json()
    STATE["integrators"].append(d["integrator_id"])
    assert d.get("empresa_integradora_id")
    STATE["companies"].append(d["empresa_integradora_id"])
    c = s.get(f"{API}/integrator-companies/{d['empresa_integradora_id']}").json()
    assert c["ficha_incompleta"] is True and c["app_count"] == 1
    STATE["auto_app"] = d["integrator_id"]


def test_move_app(s):
    nat = STATE["nat"]
    r = s.put(f"{API}/integrators/{STATE['app1']}/company", json={"empresa_integradora_id": nat["empresa_id"]})
    assert r.status_code == 200, r.text
    g = s.get(f"{API}/integrator-companies/{nat['empresa_id']}").json()
    assert any(a["integrator_id"] == STATE["app1"] for a in g["apps"])
    rows = s.get(f"{API}/integrators").json()
    row = next(x for x in rows if x["integrator_id"] == STATE["app1"])
    assert row["name"] == nat["razon_social"]
    assert s.put(f"{API}/integrators/{STATE['app1']}/company", json={"empresa_integradora_id": "emp_nope"}).status_code == 404
    assert s.put(f"{API}/integrators/int_nope/company", json={"empresa_integradora_id": nat["empresa_id"]}).status_code == 404


def test_rename_propagates(s):
    nat = STATE["nat"]
    new = f"QA Persona Natural Renombrada {SUF}"
    body = payload(tipo="Natural", razon=new, rif=nat["rif"], contacts=nat["contacts"])
    r = s.put(f"{API}/integrator-companies/{nat['empresa_id']}", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["razon_social"] == new
    rows = s.get(f"{API}/integrators").json()
    row = next(x for x in rows if x["integrator_id"] == STATE["app1"])
    assert row["name"] == new
    # contactos conservan contact_id
    assert [c["contact_id"] for c in r.json()["contacts"]] == [c["contact_id"] for c in nat["contacts"]]


def test_delete_with_apps_blocked(s):
    r = s.delete(f"{API}/integrator-companies/{STATE['nat']['empresa_id']}")
    assert r.status_code == 400


def test_delete_non_admin_forbidden(s):
    tok = _login({"email": "kherrera@megasoft.com.ve", "password": "Kherrera2026*Qa"})
    if not tok:
        pytest.skip("non-admin login unavailable")
    r = requests.delete(f"{API}/integrator-companies/{STATE['jur']['empresa_id']}", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_audit_trail(s):
    eid = STATE["jur"]["empresa_id"]
    r = s.get(f"{API}/audit-trails", params={"registro": eid, "modules": "Integradores"})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    actions = {i["accion"] for i in items}
    print("audit actions:", actions, [i.get("entidad") for i in items][:3])
    assert "CREATE" in actions and "UPDATE" in actions  # UPDATE = RIF upload


# --- Técnicos de proyecto ---
def test_implementation_fields_technicians(s):
    projs = s.get(f"{API}/projects").json()
    projs = projs if isinstance(projs, list) else projs.get("items", projs.get("projects", []))
    p = projs[0]
    pid = p["project_id"]
    orig = s.get(f"{API}/projects/{pid}").json()
    keep = {"integrator_id": orig.get("integrator_id"), "empresa_integradora_id": orig.get("empresa_integradora_id"),
            "integration_technicians": orig.get("integration_technicians") or [],
            "integrator_name": orig.get("integrator_name"), "integrator_app_name": orig.get("integrator_app_name")}
    try:
        bad = s.put(f"{API}/projects/{pid}/implementation-fields",
                    json={"integration_technicians": [{"name": "QA T", "email": "nope"}]})
        assert bad.status_code == 400
        techs = [{"name": f"QA Tec {i}", "phone": "0414", "email": f"qa.tec{i}.{SUF}@example.com", "role": "Dev"} for i in range(3)]
        r = s.put(f"{API}/projects/{pid}/implementation-fields",
                  json={"integrator_id": STATE["auto_app"], "empresa_integradora_id": STATE["companies"][-1], "integration_technicians": techs})
        assert r.status_code == 200, r.text
        got = s.get(f"{API}/projects/{pid}").json()
        assert [t["name"] for t in got["integration_technicians"]] == [t["name"] for t in techs]
        assert got["integrator_id"] == STATE["auto_app"]
        rows = s.get(f"{API}/integrators").json()
        row = next(x for x in rows if x["integrator_id"] == STATE["auto_app"])
        emails = {(c.get("email") or "").lower() for c in row.get("contacts") or []}
        assert all(t["email"] in emails for t in techs)
        sug = s.get(f"{API}/integrator-companies/technicians", params={"integrator_id": STATE["auto_app"]})
        assert sug.status_code == 200
        assert {t["email"] for t in techs} <= {x["email"] for x in sug.json()}
    finally:
        s.put(f"{API}/projects/{pid}/implementation-fields", json=keep)


def test_direct_project_invalid_tech_email(s):
    clients = s.get(f"{API}/clients").json()
    clients = clients if isinstance(clients, list) else clients.get("items", clients.get("clients", []))
    r = s.post(f"{API}/direct-projects", json={"client_id": clients[0]["client_id"], "quote_type": "GATEWAY", "cantidad_cajas": 1,
                                                 "integration_technicians": [{"name": "QA T", "email": "bad"}]})
    assert r.status_code == 400, r.text
    assert "técnico" in r.json()["detail"].lower()
