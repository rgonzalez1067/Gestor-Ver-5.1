#!/bin/bash
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)
TOKEN=$(curl -s -X POST $API/api/auth/login -H 'Content-Type: application/json' -d '{"email":"rgonzalez@megasoft.com.ve","password":"MegaSoft2026*"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['session_token'])")
H="Authorization: Bearer $TOKEN"
PID=$(curl -s "$API/api/projects?limit=1" -H "$H" | python3 -c "import sys,json;d=json.load(sys.stdin);d=d.get('items',d) if isinstance(d,dict) else d;print(d[0]['project_id'])")
GID=$(curl -s "$API/api/grupos-economicos" -H "$H" | python3 -c "import sys,json;d=json.load(sys.stdin);d=d.get('items',d) if isinstance(d,dict) else d;print(d[0].get('group_id',''))" 2>/dev/null)
curl -s -o /tmp/r_irr.pdf -w "irregular %{http_code}\n" "$API/api/reports/sales/irregular-quotes/pdf" -H "$H"
curl -s -o /tmp/r_avance.pdf -w "avance %{http_code}\n" "$API/api/projects/$PID/report/avance/pdf" -H "$H"
curl -s -o /tmp/r_work.pdf -w "workload %{http_code}\n" "$API/api/projects/reports/workload-pdf" -H "$H"
curl -s -o /tmp/r_grp.pdf -w "grupo %{http_code}\n" "$API/api/grupos-economicos/$GID/export-pdf" -H "$H"
cd /app/backend && python3 -c "
import fitz
for n in ['irr','avance','work','grp']:
    try:
        d=fitz.open(f'/tmp/r_{n}.pdf'); print(n,len(d), all('Gestor - CRM' in p.get_text() for p in d))
        d[len(d)-1].get_pixmap(dpi=40, clip=fitz.Rect(0,0,850,160)).save(f'/app/memory/r_{n}.png')
    except Exception as e: print(n,'ERR',e)
"
