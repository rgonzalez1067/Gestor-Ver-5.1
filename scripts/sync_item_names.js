// Alinea el nombre de los ítems de Inventario y Seriales con el nombre actual del Catálogo.
// Simulación: mongosh "<MONGO_URL>/<DB_NAME>" /tmp/sync_item_names.js
// Aplicar:    mongosh "<MONGO_URL>/<DB_NAME>" --eval 'var APPLY=true' /tmp/sync_item_names.js
const apply = typeof APPLY !== "undefined" && APPLY === true;
const cols = ["inventory_movements", "serial_assignments"];
let total = 0;
db.hardware.find({}, { _id: 0, hardware_id: 1, name: 1 }).forEach(hw => {
  const name = (hw.name || "").trim();
  if (!name) return;
  cols.forEach(col => {
    const q = { item_id: hw.hardware_id, item_name: { $ne: name } };
    const n = db.getCollection(col).countDocuments(q);
    if (!n) return;
    const old = db.getCollection(col).distinct("item_name", q);
    print(`[${col}] ${hw.hardware_id}: ${n} registro(s)  "${old.join('" / "')}"  →  "${name}"`);
    if (apply) db.getCollection(col).updateMany(q, { $set: { item_name: name } });
    total += n;
  });
});
print(total === 0 ? "Todo alineado: no hay nombres desactualizados."
  : (apply ? `APLICADO: ${total} registro(s) actualizados.` : `SIMULACIÓN: ${total} registro(s) por actualizar. Ejecuta con APPLY=true para aplicar.`));
