# Helper Iter 354: inspeccionar fila Servicio Express de una cotización (BD + PDF) y borrar cotizaciones de prueba
import sys, io, json, requests
API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0] + "/api"
s = requests.Session()
d = s.post(f"{API}/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"}).json()
s.headers.update({"Authorization": f"Bearer {d.get('session_token')}"})
cmd, ids = sys.argv[1], sys.argv[2:]
if cmd == "show":
    for qid in ids:
        q = s.get(f"{API}/quotes/{qid}").json()
        print(qid, q.get("quote_number"), q.get("quote_type"), "servicio_express=", q.get("servicio_express"), "total=", q.get("total_usd") or q.get("total"))
        for it in q.get("services", []):
            if "express" in (it.get("item_name") or "").lower() or it.get("express"):
                print("  services:", json.dumps({k: it.get(k) for k in it if k not in ("description",)}, ensure_ascii=False)[:500])
        for it in q.get("pg_setup_items", []) or []:
            print("  pg_setup:", it)
        pdf_url = q.get("pdf_url") or q.get("pdf_path")
        print("  pdf:", pdf_url)
elif cmd == "pdf":
    from pypdf import PdfReader
    for qid in ids:
        r = s.get(f"{API}/quotes/{qid}/pdf")
        print(qid, r.status_code, r.headers.get("content-type"))
        if r.ok and r.content[:4] == b"%PDF":
            txt = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
            for line in txt.splitlines():
                if "express" in line.lower() or "Producción" in line:
                    print("  PDF:", line)
elif cmd == "del":
    for qid in ids:
        print("delete", qid, s.delete(f"{API}/quotes/{qid}").status_code)
