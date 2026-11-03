import os, requests, json
BASE = "https://quote-overhaul.preview.emergentagent.com"
s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "admin123"})
print("login", r.status_code)
tok = r.json().get("session_token")
if tok:
    s.headers["Authorization"] = f"Bearer {tok}"
clients = s.get(f"{BASE}/api/clients").json()
quotes = s.get(f"{BASE}/api/quotes").json()
if isinstance(clients, dict): clients = clients.get("clients") or clients.get("items")
if isinstance(quotes, dict): quotes = quotes.get("quotes") or quotes.get("items")
print("clients", len(clients), "quotes", len(quotes))
by = {c["client_id"]: c for c in clients}
active = [q for q in quotes if not q.get("archived")]
ids = {q.get("client_id") for q in active if q.get("client_id")}
groups = {}
for c in clients:
    if c["client_id"] not in ids: continue
    p = by.get(c.get("parent_client_id")) or c if c.get("parent_client_id") else c
    gid = c.get("grupo_economico_id") or p.get("grupo_economico_id")
    gn = (c.get("grupo_economico") or p.get("grupo_economico") or "").strip()
    if not gid and not gn: continue
    k = gid or gn.upper()
    groups.setdefault(k, {"name": gn, "ids": []})["ids"].append(c["client_id"])
for k, g in sorted(groups.items(), key=lambda x: x[1]["name"]):
    n = sum(1 for q in active if q.get("client_id") in g["ids"])
    print(k, "|", g["name"], "|", ",".join(g["ids"]), "| active quotes:", n)
# all groups in catalog
allg = {(c.get("grupo_economico_id") or c.get("grupo_economico")) for c in clients if c.get("grupo_economico_id") or c.get("grupo_economico")}
print("total groups in catalog", len(allg))
for c in clients:
    if "salus" in (c.get("legal_name") or "").lower() or "brasero" in (c.get("fantasy_name") or "").lower():
        print("CLIENT", c["client_id"], c.get("legal_name"), "|", c.get("fantasy_name"), "| parent", c.get("parent_client_id"), "| grp", c.get("grupo_economico_id"), c.get("grupo_economico"), "| hasquote", c["client_id"] in ids)
