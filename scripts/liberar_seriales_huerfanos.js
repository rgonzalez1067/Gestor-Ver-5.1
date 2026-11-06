// Libera seriales huérfanos: los de ítems eliminados de Bienes y Servicios (hardware).
// Uso:  mongosh "<MONGO_URL>/<DB_NAME>" --eval "var MODO='ver'"    -f liberar_seriales_huerfanos.js   (solo muestra)
//       mongosh "<MONGO_URL>/<DB_NAME>" --eval "var MODO='borrar'" -f liberar_seriales_huerfanos.js   (elimina)
var modo = (typeof MODO !== 'undefined') ? MODO : 'ver';
var itemsVivos = db.hardware.distinct('hardware_id');
var huerfanosMov = db.inventory_movements.distinct('item_id', { item_id: { $nin: itemsVivos } });
var huerfanosAsg = db.serial_assignments.distinct('item_id', { item_id: { $nin: itemsVivos } });
var itemIds = Array.from(new Set(huerfanosMov.concat(huerfanosAsg))).filter(function (x) { return x; });

if (itemIds.length === 0) {
  print('No hay seriales huérfanos. Nada que hacer.');
  quit();
}

var serials = new Set();
db.inventory_movements.find({ item_id: { $in: itemIds } }, { serials: 1 }).forEach(function (m) {
  (m.serials || []).forEach(function (s) { serials.add(s); });
});
db.serial_assignments.find({ item_id: { $in: itemIds } }, { serial: 1 }).forEach(function (a) { if (a.serial) serials.add(a.serial); });
var lista = Array.from(serials);

print('Ítems eliminados con inventario: ' + itemIds.length);
itemIds.forEach(function (id) {
  var m = db.inventory_movements.findOne({ item_id: id }, { item_name: 1 });
  print('  - ' + id + '  (' + ((m && m.item_name) || 'sin nombre') + ')');
});
print('Movimientos a eliminar:    ' + db.inventory_movements.countDocuments({ item_id: { $in: itemIds } }));
print('Asignaciones a eliminar:   ' + db.serial_assignments.countDocuments({ item_id: { $in: itemIds } }));
print('Seriales en lista negra:   ' + db.serial_blacklist.countDocuments({ serial: { $in: lista } }));
print('Seriales que se liberan:   ' + lista.length);
print('  ' + lista.slice(0, 50).join(', ') + (lista.length > 50 ? ' ...' : ''));

if (modo !== 'borrar') {
  print('\nModo VER: no se borró nada. Ejecute con MODO=\'borrar\' para eliminar.');
  quit();
}

var r1 = db.inventory_movements.deleteMany({ item_id: { $in: itemIds } });
var r2 = db.serial_assignments.deleteMany({ item_id: { $in: itemIds } });
var r3 = db.serial_blacklist.deleteMany({ serial: { $in: lista } });
print('\nEliminados -> movimientos: ' + r1.deletedCount + ', asignaciones: ' + r2.deletedCount + ', lista negra: ' + r3.deletedCount);
print('Listo. Ya puede volver a cargar esos seriales en el nuevo ítem.');
