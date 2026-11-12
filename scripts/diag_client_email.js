// Uso: mongosh "<MONGO_URL>/<DB_NAME>" --eval 'var QN="COT-XXXX"' /app/scripts/diag_client_email.js
const q = db.quotes.findOne({ quote_number: QN }, { _id: 0, quote_number: 1, client_id: 1, client_email: 1, quote_category: 1, quote_type: 1, segment: 1 });
if (!q) { print("Cotización no encontrada: " + QN); quit(); }
print("== Cotización"); printjson(q);
const withEmail = (d) => ((d && d.contacts) || []).filter(c => (c.email || "").trim());
const c = q.client_id ? db.clients.findOne({ client_id: q.client_id }, { _id: 0 }) : null;
if (!c) { print("!! client_id de la cotización NO existe en clients → causa del mensaje"); quit(); }
print("== Cliente (" + c.client_id + ") is_branch=" + !!c.is_branch + " parent_id=" + (c.parent_id || c.parent_client_id || "-"));
print("contacts: " + JSON.stringify(c.contacts || []));
print("contact1 (legacy): " + JSON.stringify(c.contact1 || null));
print("email en raíz (NO se usa): " + (c.email || "-"));
const levels = [["sucursal/RIF", c]];
const pid = c.parent_id || c.parent_client_id;
const p = pid ? db.clients.findOne({ client_id: pid }, { _id: 0 }) : c;
if (pid) levels.push(["RIF principal", p]);
let gid = p && p.grupo_economico_id;
if (p && p.marca_id) { const b = db.brands.findOne({ brand_id: p.marca_id }, { _id: 0 }); if (b) { levels.push(["Marca " + b.name, b]); gid = b.group_id || gid; } }
if (gid) { const g = db.economic_groups.findOne({ group_id: gid }, { _id: 0 }); if (g) levels.push(["Grupo " + g.name, g]); }
print("== Contactos con email por nivel");
levels.forEach(([n, d]) => print(n + ": " + withEmail(d).map(x => x.email).join(", ") || "(ninguno)"));
const ok = (q.client_email || "").trim() || levels.some(([, d]) => withEmail(d).length);
print(ok ? "OK: se encontró email; el mensaje NO debería salir." : "!! Ningún nivel tiene contactos[].email → por eso sale el mensaje");
