import { Input } from '../../ui/input';
import { Store, Calculator } from 'lucide-react';

// Grilla de sucursales seleccionables por RIF con cajas por tienda (modo desglose).
// rifs: [{client_id, rif, legal_name, marca_name, stores:[{client_id,name,is_principal}]}]
// picked: {rifId: [storeIds]}, boxes: {storeId: n}
export const StoresBoxesGrid = ({ rifs, picked, onPick, boxes, onBoxes, desglose, onDesglose, total }) => (
  <div className="border border-slate-200 rounded-lg bg-white" data-testid="scope-stores-grid">
    <div className="px-3 py-2 border-b bg-slate-50 flex items-center justify-between gap-3 flex-wrap">
      <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5"><Store size={13} /> Sucursales / Tiendas</span>
      <div className="flex gap-1" role="radiogroup" data-testid="scope-boxes-mode">
        {[[true, 'Desglose por tienda'], [false, 'Carga global (Nro de Cajas)']].map(([v, l]) => (
          <button key={l} type="button" role="radio" aria-checked={desglose === v} onClick={() => onDesglose(v)}
            data-testid={`scope-mode-${v ? 'desglose' : 'global'}`}
            className={`px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-colors ${desglose === v ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400'}`}>{l}</button>
        ))}
      </div>
    </div>
    <div className="max-h-72 overflow-y-auto divide-y">
      {rifs.length === 0 && <p className="text-xs text-slate-400 italic p-3">Seleccione al menos un RIF.</p>}
      {rifs.map(r => {
        const sel = picked[r.client_id] || [];
        const allOn = r.stores.length > 0 && r.stores.every(s => sel.includes(s.client_id));
        return (
          <div key={r.client_id} data-testid={`scope-rif-block-${r.client_id}`}>
            <div className="px-3 py-1.5 bg-indigo-50/60 flex items-center gap-2 text-xs">
              <span className="font-mono text-slate-500">{r.rif}</span>
              <span className="font-semibold text-slate-800 truncate">{r.legal_name}</span>
              {r.marca_name && <span className="text-[10px] text-teal-700 bg-teal-50 px-1.5 rounded">{r.marca_name}</span>}
              <button type="button" className="ml-auto text-[11px] text-indigo-600 hover:underline" data-testid={`scope-stores-all-${r.client_id}`}
                onClick={() => onPick(r.client_id, allOn ? [] : r.stores.map(s => s.client_id))}>{allOn ? 'Quitar todas' : 'Todas'}</button>
            </div>
            {r.stores.map(s => {
              const on = sel.includes(s.client_id);
              return (
                <div key={s.client_id} className="px-3 py-1 flex items-center gap-2 text-xs" data-testid={`scope-store-${s.client_id}`}>
                  <input type="checkbox" checked={on} data-testid={`scope-store-check-${s.client_id}`} className="accent-indigo-600"
                    onChange={() => onPick(r.client_id, on ? sel.filter(x => x !== s.client_id) : [...sel, s.client_id])} />
                  <span className={`truncate ${s.is_principal ? 'font-semibold text-indigo-700' : 'text-slate-700'}`}>{s.is_principal ? `Principal · ${s.name}` : s.name}</span>
                  {desglose && on && (
                    <Input type="number" min="0" value={boxes[s.client_id] ?? ''} placeholder="Cajas" data-testid={`scope-store-boxes-${s.client_id}`}
                      onChange={e => onBoxes(s.client_id, e.target.value === '' ? '' : Math.max(parseInt(e.target.value) || 0, 0))}
                      className="ml-auto h-7 w-20 text-xs" />
                  )}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
    {desglose && (
      <div className="px-3 py-2 border-t bg-emerald-50 flex items-center justify-end gap-2 text-sm" data-testid="scope-total-boxes">
        <Calculator size={14} className="text-emerald-700" />
        <span className="text-emerald-800">Total Cajas Cotización:</span>
        <span className="font-bold text-emerald-900" data-testid="scope-total-boxes-value">{total}</span>
      </div>
    )}
  </div>
);
