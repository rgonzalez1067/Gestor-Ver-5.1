// Uso: mongosh "<MONGO_URL>/<DB_NAME>" --eval 'var HID="hwr_xxx"' /app/scripts/item_usage.js
let total = 0;
db.getCollectionNames().forEach(n => {
  if (n === "hardware") return;
  let k = 0;
  db.getCollection(n).find({}, { _id: 0 }).forEach(d => { if (JSON.stringify(d).includes(HID)) k++; });
  if (k) { print(n + ": " + k); total += k; }
});
print(total ? "EN USO: " + total + " referencias" : "SIN referencias: se puede eliminar");
