import os, requests
API = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0]
s = requests.Session()
tok = s.post(f"{API}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"}).json()["session_token"]
s.headers["Authorization"] = f"Bearer {tok}"
ok = lambda r: (r.raise_for_status() or r.json())
g = ok(s.post(f"{API}/api/grupos-economicos", json={"name": "QA4N Grupo", "contacts": [{"full_name": "Corp A", "email": "corpa@qa.com"}],
        "characteristics": {"segment": "Corporativo", "categoria_comercial": "Retail"}}))
ba = ok(s.post(f"{API}/api/marcas", json={"name": "QA4N Marca A", "group_id": g["group_id"]}))
bb = ok(s.post(f"{API}/api/marcas", json={"name": "QA4N Marca B", "group_id": g["group_id"], "contacts": [{"full_name": "Marca B", "email": "mb@qa.com"}],
        "characteristics": {"segment": "Pymes"}}))
r1 = ok(s.post(f"{API}/api/clients", json={"rif": "J990000001", "legal_name": "QA4N RIF UNO CA", "marca_id": ba["brand_id"], "grupo_economico_id": g["group_id"], "segment": "Corporativo"}))
r2 = ok(s.post(f"{API}/api/clients", json={"rif": "J990000002", "legal_name": "QA4N RIF DOS CA", "marca_id": bb["brand_id"], "grupo_economico_id": g["group_id"], "segment": "Pymes"}))
print("r1", r1["fantasy_name"], r1["grupo_economico"], r1["segment"], r1["categoria_comercial"], r1["inherit_overrides"])
for n in ("S1", "S2"):
    ok(s.post(f"{API}/api/clients/{r2['client_id']}/branches", json={"sucursal": n}))
ok(s.post(f"{API}/api/clients/{r2['client_id']}/branches", json={"sucursal": "S3", "contacts": [{"full_name": "Local C", "email": "lc@qa.com"}]}))
print("group marcas", [b["name"] for b in ok(s.get(f"{API}/api/grupos-economicos/{g['group_id']}/marcas"))])
print("brand B rifs", ok(s.get(f"{API}/api/marcas/{bb['brand_id']}/rifs")))
br = ok(s.get(f"{API}/api/clients/{r2['client_id']}/branches"))["branches"]
print("branches", [b["sucursal"] for b in br])
for c in (r1, r2, br[0], br[2]):
    cc = ok(s.get(f"{API}/api/clients/{c['client_id']}/consolidated-contacts"))["contacts"]
    print(c.get("sucursal"), c["legal_name"], [(x["scope"], x["email"], x["effective"]) for x in cc])
# propagation: change group category
ok(s.put(f"{API}/api/grupos-economicos/{g['group_id']}", json={"name": "QA4N Grupo", "contacts": [{"full_name": "Corp A", "email": "corpa@qa.com"}],
        "characteristics": {"segment": "Corporativo", "categoria_comercial": "Farmacias"}}))
print("after group change r1 cat:", ok(s.get(f"{API}/api/clients/{r1['client_id']}"))["categoria_comercial"],
      "branch cat:", ok(s.get(f"{API}/api/clients/{br[0]['client_id']}"))["categoria_comercial"])
inh = ok(s.get(f"{API}/api/clients/{br[0]['client_id']}/inheritance"))
print([(x["field"], x["value"], x["source_level"]) for x in inh["characteristics"][:3]])
if os.environ.get("KEEP") != "1":
    for b in br: s.delete(f"{API}/api/clients/{b['client_id']}")
    for c in (r1, r2): s.delete(f"{API}/api/clients/{c['client_id']}")
    for b in (ba, bb): s.delete(f"{API}/api/marcas/{b['brand_id']}")
    s.delete(f"{API}/api/grupos-economicos/{g['group_id']}")
    print("cleaned")
