#!/bin/bash
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)
TOKEN=$(curl -s -X POST $API/api/auth/login -H 'Content-Type: application/json' -d '{"email":"rgonzalez@megasoft.com.ve","password":"MegaSoft2026*"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['session_token'])")
H="Authorization: Bearer $TOKEN"
POL=$(curl -s $API/api/admin/security-policy -H "$H")
echo "$POL" | head -c 300; echo
NEW=$(echo "$POL" | python3 -c "import sys,json;d=json.load(sys.stdin);d['lockout_minutes']=(d.get('lockout_minutes') or 15)+1;print(json.dumps(d))")
curl -s -X PUT $API/api/admin/security-policy -H "$H" -H 'Content-Type: application/json' -d "$NEW" | head -c 100; echo
BACK=$(echo "$NEW" | python3 -c "import sys,json;d=json.load(sys.stdin);d['lockout_minutes']-=1;print(json.dumps(d))")
curl -s -X PUT $API/api/admin/security-policy -H "$H" -H 'Content-Type: application/json' -d "$BACK" > /dev/null
curl -s "$API/api/audit-trails?page_size=5" -H "$H" | python3 -m json.tool | head -60
