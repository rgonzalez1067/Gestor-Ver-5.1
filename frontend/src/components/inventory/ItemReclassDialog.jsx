import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Shuffle, Search } from 'lucide-react';
import api from '../../utils/api';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';

// Solo Admin: transfiere unidades/seriales de un producto a otro del MISMO almacén (corrige productos duplicados).
export const ItemReclassDialog = ({ item, warehouseId, warehouseName, onClose, onDone }) => {
  const [targets, setTargets] = useState([]);
  const [requiresSerial, setRequiresSerial] = useState(false);
  const [dest, setDest] = useState('');
  const [q, setQ] = useState('');
  const [qty, setQty] = useState(1);
  const [sel, setSel] = useState([]);
  const [sq, setSq] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!item) return;
    setDest(''); setQ(''); setQty(1); setSel([]); setSq(''); setNotes('');
    api.get('/admin/inventory/reclass-targets', { params: { item_id: item.item_id } })
      .then(r => { setTargets(r.data.items || []); setRequiresSerial(r.data.requires_serial); })
      .catch(e => toast.error(e.response?.data?.detail || 'No se pudieron cargar los productos'));
  }, [item]);

  const filtered = useMemo(() => targets.filter(t => t.name.toLowerCase().includes(q.toLowerCase())).slice(0, 50), [targets, q]);
  const serials = useMemo(() => (item?.serials || []).filter(s => s.toLowerCase().includes(sq.toLowerCase())), [item, sq]);
  const count = requiresSerial ? sel.length : Number(qty) || 0;
  const max = item?.quantity || 0;
  const destName = targets.find(t => t.item_id === dest)?.name;

  const toggle = (s) => setSel(p => (p.includes(s) ? p.filter(x => x !== s) : [...p, s]));
  const submit = async () => {
    if (!window.confirm(`¿Transferir ${count} unidad(es) de «${item.item_name}» a «${destName}» en ${warehouseName}?`)) return;
    setSaving(true);
    try {
      await api.post('/admin/inventory/item-reclass', {
        warehouse_id: warehouseId, source_item_id: item.item_id, dest_item_id: dest,
        quantity: count, serials: requiresSerial ? sel : [], notes,
      });
      toast.success(`${count} unidad(es) transferidas a ${destName}`);
      onDone?.(); onClose();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error en la transferencia interna'); }
    finally { setSaving(false); }
  };

  const valid = dest && count > 0 && count <= max && notes.trim().length >= 5;
  return (
    <Dialog open={!!item} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="item-reclass-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Shuffle size={18} className="text-violet-600" />Transferencia interna entre productos</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Almacén: <b>{warehouseName}</b></p>
            <p className="font-semibold text-slate-800 mt-1">Origen: {item?.item_name}</p>
            <p className="text-xs text-slate-500">Disponible: <b data-testid="reclass-available">{max}</b>{requiresSerial ? ' (con serial)' : ''}</p>
          </div>
          <div>
            <Label className="text-xs">Producto destino * <span className="text-slate-400">({requiresSerial ? 'solo productos con serial' : 'solo productos sin serial'})</span></Label>
            <div className="relative mt-1">
              <Search size={13} className="absolute left-2 top-2.5 text-slate-400" />
              <Input value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar producto..." className="pl-7 h-8" data-testid="reclass-dest-search" />
            </div>
            <div className="mt-1 max-h-36 overflow-y-auto border border-slate-200 rounded-md divide-y divide-slate-100">
              {filtered.map(t => (
                <button key={t.item_id} type="button" onClick={() => setDest(t.item_id)}
                  className={`w-full text-left px-3 py-1.5 text-xs hover:bg-violet-50 ${dest === t.item_id ? 'bg-violet-100 font-semibold' : ''}`}
                  data-testid={`reclass-dest-${t.item_id}`}>{t.name} <span className="text-slate-400">· {t.type}</span></button>
              ))}
              {filtered.length === 0 && <p className="px-3 py-2 text-xs text-slate-400">Sin coincidencias</p>}
            </div>
          </div>
          {requiresSerial ? (
            <div>
              <Label className="text-xs">Seriales a transferir * ({sel.length} seleccionados)</Label>
              <div className="flex gap-2 mt-1">
                <Input value={sq} onChange={e => setSq(e.target.value)} placeholder="Filtrar seriales..." className="h-8" data-testid="reclass-serial-search" />
                <Button type="button" size="sm" variant="outline" className="h-8 text-xs" onClick={() => setSel(Array.from(new Set([...sel, ...serials])))} data-testid="reclass-select-all">Todos</Button>
                <Button type="button" size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setSel([])}>Ninguno</Button>
              </div>
              <div className="mt-1 max-h-40 overflow-y-auto border border-slate-200 rounded-md grid grid-cols-2 gap-x-2 p-2">
                {serials.map(s => (
                  <label key={s} className="flex items-center gap-1.5 text-xs font-mono py-0.5 cursor-pointer">
                    <input type="checkbox" checked={sel.includes(s)} onChange={() => toggle(s)} data-testid={`reclass-serial-${s}`} />{s}
                  </label>
                ))}
                {serials.length === 0 && <p className="text-xs text-slate-400 col-span-2">Sin seriales disponibles</p>}
              </div>
            </div>
          ) : (
            <div>
              <Label className="text-xs">Cantidad a transferir *</Label>
              <Input type="number" min={1} max={max} value={qty} onChange={e => setQty(e.target.value)} className="h-8 w-32 mt-1" data-testid="reclass-quantity" />
            </div>
          )}
          <div>
            <Label className="text-xs">Motivo *</Label>
            <Textarea rows={2} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Ej.: Producto duplicado por error de nombre" data-testid="reclass-notes" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="reclass-cancel">Cancelar</Button>
          <Button onClick={submit} disabled={!valid || saving} className="bg-violet-600 hover:bg-violet-700 text-white" data-testid="reclass-confirm">
            {saving && <Loader2 size={14} className="mr-1 animate-spin" />}Transferir {count > 0 ? count : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
