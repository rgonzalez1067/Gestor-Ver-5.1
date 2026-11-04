# Helper Iter 353: crear/eliminar ítem temporal 'Servicio Express' y contar estatus de productos de banco
import sys, requests
API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0] + "/api"
s = requests.Session()
d = s.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"}).json()
s.headers.update({"Authorization": f"Bearer {d.get('session_token') or d.get('token')}"})
cmd = sys.argv[1]
svcs = s.get(f"{API}/services").json()
ex = [x for x in svcs if (x.get("name") or "").strip().lower() == "servicio express"]
if cmd == "status":
    print("express items:", [(x["service_id"], x.get("setup_cost_conventional"), x.get("setup_cost_outsourcing")) for x in ex])
    from collections import Counter
    c = Counter(p.get("operational_status") for b in s.get(f"{API}/banks").json() for p in b.get("products", []))
    print("bank statuses:", dict(c))
    qs = s.get(f"{API}/quotes").json()
    qs = qs if isinstance(qs, list) else qs.get("quotes", [])
    print("TEST quotes:", [(q["quote_id"], q.get("notes")) for q in qs if "TEST" in (q.get("notes") or "") or "TEST" in (q.get("client_name") or "")])
elif cmd == "create":
    r = s.post(f"{API}/services", json={"name": "Servicio Express", "service_type": "Servicio", "application_type": "setup",
                                         "setup_cost_conventional": 100, "setup_cost_outsourcing": 20})
    print(r.status_code, r.json().get("service_id"))
elif cmd == "delquote":
    for q in sys.argv[2:]:
        print("delete", q, s.delete(f"{API}/quotes/{q}").status_code)
