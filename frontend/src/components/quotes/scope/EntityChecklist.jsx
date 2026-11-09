import { useState, useMemo } from 'react';
import { Checkbox } from '../../ui/checkbox';
import { Search, CheckSquare, Square } from 'lucide-react';

const az = (a, b) => (a.label || '').localeCompare(b.label || '', 'es', { sensitivity: 'base' });

// Lista A-Z con buscador. multiple=false → selección única (radio).
// items: [{id, label, sub?, group?}]; selected: ids[]
export const EntityChecklist = ({ title, items, selected, onChange, multiple = true, grouped = false, testId, emptyText = 'Sin registros.' }) => {
  const [q, setQ] = useState('');
  const list = useMemo(() => {
    const t = q.trim().toLowerCase();
    return items.map(i => ({ ...i, label: (i.label || '').trim() })).sort(az).filter(i => !t || `${i.label} ${i.sub || ''}`.toLowerCase().includes(t));
  }, [items, q]);
  const groups = useMemo(() => {
    if (!grouped) return [[null, list]];
    const m = new Map();
    list.forEach(i => { const g = i.group || 'Sin marca'; m.set(g, [...(m.get(g) || []), i]); });
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0], 'es', { sensitivity: 'base' }));
  }, [list, grouped]);
  const toggle = (id) => {
    if (!multiple) return onChange(selected.includes(id) ? [] : [id]);
    onChange(selected.includes(id) ? selected.filter(x => x !== id) : [...selected, id]);
  };
  const setMany = (ids, on) => onChange(on ? [...new Set([...selected, ...ids])] : selected.filter(x => !ids.includes(x)));
  const allIds = list.map(i => i.id);
  const allOn = allIds.length > 0 && allIds.every(id => selected.includes(id));

  return (
    <div className="border border-slate-200 rounded-lg bg-white flex flex-col min-h-0" data-testid={testId}>
      <div className="px-3 py-2 border-b bg-slate-50 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-slate-700">{title} <span className="text-slate-400">({selected.length}/{items.length})</span></span>
        {multiple && items.length > 0 && (
          <button type="button" onClick={() => setMany(allIds, !allOn)} className="text-[11px] font-medium text-indigo-600 hover:underline flex items-center gap-1" data-testid={`${testId}-select-all`}>
            {allOn ? <><Square size={12} /> Quitar todas</> : <><CheckSquare size={12} /> Seleccionar todas</>}
          </button>
        )}
      </div>
      <div className="px-2 py-1.5 border-b relative">
        <Search size={13} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar..." data-testid={`${testId}-search`}
          className="w-full h-8 pl-7 pr-2 text-xs border rounded-md outline-none focus:ring-1 focus:ring-indigo-300" />
      </div>
      <div className="overflow-y-auto max-h-56">
        {list.length === 0 && <p className="text-xs text-slate-400 italic p-3">{emptyText}</p>}
        {groups.map(([g, rows]) => (
          <div key={g || 'all'}>
            {g && (
              <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wide bg-teal-50 text-teal-800 border-y border-teal-100 flex justify-between" data-testid={`${testId}-group-${g}`}>
                <span>{g}</span>
                {multiple && <button type="button" className="normal-case hover:underline" onClick={() => setMany(rows.map(r => r.id), !rows.every(r => selected.includes(r.id)))}>
                  {rows.every(r => selected.includes(r.id)) ? 'Quitar' : 'Todos'}
                </button>}
              </div>
            )}
            {rows.map(i => (
              <label key={i.id} className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-indigo-50/50 cursor-pointer" data-testid={`${testId}-item-${i.id}`}>
                <Checkbox checked={selected.includes(i.id)} onCheckedChange={() => toggle(i.id)} data-testid={`${testId}-check-${i.id}`} />
                <span className="font-medium text-slate-800 truncate">{i.label}</span>
                {i.sub && <span className="ml-auto text-[10px] text-slate-400 font-mono shrink-0">{i.sub}</span>}
              </label>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};
