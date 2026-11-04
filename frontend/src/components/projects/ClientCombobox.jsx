import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Input } from '../ui/input';
import { Search } from 'lucide-react';

// Combobox de cliente con búsqueda predictiva por RIF, Razón Social,
// Nombre Comercial y Grupo Económico. Devuelve el cliente completo al elegir.
export const ClientCombobox = ({ clients, value, displayName, onSelect, testid = 'master-client', compact = false }) => {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return clients.slice(0, 50);
    return clients.filter((c) =>
      (c.legal_name || '').toLowerCase().includes(s) ||
      (c.fantasy_name || '').toLowerCase().includes(s) ||
      (c.rif || '').toLowerCase().includes(s) ||
      (c.grupo_economico || c.economic_group || '').toLowerCase().includes(s)
    ).slice(0, 50);
  }, [clients, q]);

  const selected = clients.find((c) => c.client_id === value);
  const label = selected
    ? (compact ? `${selected.rif || 'sin RIF'} · ${selected.fantasy_name || selected.legal_name}` : (selected.legal_name || selected.fantasy_name))
    : (displayName || '');

  return (
    <div className="relative" ref={ref} data-testid={`${testid}-combobox`}>
      <button type="button" onClick={() => setOpen(v => !v)}
        className={`w-full h-8 px-2 border border-slate-200 rounded-md bg-white text-left ${compact ? 'text-xs' : 'text-sm'} hover:border-slate-300 focus:border-blue-500 focus:outline-none flex items-center justify-between`}
        data-testid={`${testid}-trigger`}>
        <span className={label ? 'text-slate-900 truncate' : 'text-slate-400'}>{label || 'Seleccionar comercio...'}</span>
        <Search size={14} className="text-slate-400 flex-shrink-0" />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full min-w-[280px] max-h-72 bg-white border border-slate-200 rounded-md shadow-xl flex flex-col">
          <div className="p-2 border-b border-slate-100">
            <Input autoFocus value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar por nombre comercial, razón social o RIF..." className="h-8 text-sm"
              data-testid={`${testid}-search`} />
          </div>
          <div className="overflow-y-auto flex-1 py-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-4 text-xs text-slate-400 text-center">Sin resultados</div>
            ) : filtered.map((c, idx) => (
              <button key={`${c.client_id}-${idx}`} type="button"
                onClick={() => { onSelect(c); setOpen(false); setQ(''); }}
                className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm border-b border-slate-50 last:border-b-0"
                data-testid={`${testid}-opt-${c.client_id}`}>
                <div className="font-medium text-slate-800 truncate">{c.fantasy_name || c.legal_name}</div>
                <div className="text-xs text-slate-500 truncate">{c.rif || 'sin RIF'}{c.fantasy_name && c.legal_name ? ` · ${c.legal_name}` : ''}{(c.grupo_economico || c.economic_group) ? ` · ${c.grupo_economico || c.economic_group}` : ''}</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
