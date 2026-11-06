#!/bin/bash
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)
TOKEN=$(curl -s -X POST $API/api/auth/login -H 'Content-Type: application/json' -d '{"email":"rgonzalez@megasoft.com.ve","password":"MegaSoft2026*"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['session_token'])")
H="Authorization: Bearer $TOKEN"
curl -s -o /tmp/r_banks.pdf -w "banks %{http_code}\n" "$API/api/banks/report/products-by-bank/pdf" -H "$H"
curl -s -o /tmp/r_services.pdf -w "services %{http_code}\n" "$API/api/services/report/banks-by-product/pdf" -H "$H"
curl -s -o /tmp/r_integ.pdf -w "integ %{http_code}\n" "$API/api/integrators/export/pdf" -H "$H"
cd /app/backend && python3 -c "
import fitz
for n in ['banks','services','integ']:
    try:
        d=fitz.open(f'/tmp/r_{n}.pdf'); print(n,len(d), [('Gestor - CRM' in p.get_text(), 'MegaNexus' in p.get_text()) for p in d][:4])
        d[min(1,len(d)-1)].get_pixmap(dpi=45, clip=fitz.Rect(0,0,620,200)).save(f'/app/memory/r_{n}.png')
    except Exception as e: print(n,'ERR',e)
"
