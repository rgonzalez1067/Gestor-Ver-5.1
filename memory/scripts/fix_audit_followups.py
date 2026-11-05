p = '/app/backend/routes/audit_trails.py'
s = open(p).read()
a = s.index('    def _build():\n')
b = s.index('    buf = await asyncio.to_thread(_build)')
new_block = '''    def _build():
        for d in docs:
            ws.append([
                d.get("fecha_hora", ""), d.get("modulo", ""), d.get("entidad", ""), d.get("registro_id", ""), d.get("accion", ""),
                d.get("usuario_nombre", ""), d.get("usuario_email", ""), d.get("ip_origen", ""), d.get("endpoint", ""),
                ", ".join(d.get("campos_modificados") or []),
                json.dumps(d.get("valores_anteriores"), ensure_ascii=False, default=str)[:32000] if d.get("valores_anteriores") is not None else "",
                json.dumps(d.get("valores_nuevos"), ensure_ascii=False, default=str)[:32000] if d.get("valores_nuevos") is not None else "",
            ])
        for col, w in zip("ABCDEFGHIJKL", (22, 20, 20, 26, 10, 24, 28, 16, 36, 40, 60, 60)):
            ws.column_dimensions[col].width = w
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return out

'''
s = s[:a] + new_block + s[b:]
open(p, 'w').write(s)

p = '/app/frontend/src/pages/AuditTrailsPage.jsx'
s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)
rep("import { useNavigate } from 'react-router-dom';", "import { useNavigate, Navigate } from 'react-router-dom';")
rep("""  const isAdmin = (() => { try { return JSON.parse(localStorage.getItem('user') || '{}')?.role === 'admin'; } catch { return false; } })();
""", """  const me = (() => { try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; } })();
  const isAdmin = me?.role === 'admin';
  const canAudit = isAdmin || (me?.special_permissions || []).includes('configuracion:auditor');
""")
rep("""  useEffect(() => { api.get('/audit-trails/filters')""", """  useEffect(() => { if (canAudit) api.get('/audit-trails/filters')""")
rep("""  useEffect(() => { load(); }, [load]);
""", """  useEffect(() => { if (canAudit) load(); }, [load, canAudit]);
""")
rep("""  return (
    <div className="flex min-h-screen bg-slate-50">""", """  if (!canAudit) return <Navigate to="/settings" replace />;

  return (
    <div className="flex min-h-screen bg-slate-50">""")
open(p, 'w').write(s)
print('ok')
