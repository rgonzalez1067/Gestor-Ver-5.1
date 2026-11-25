import { useState, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Label } from '../../ui/label';
import { Search, Landmark, Building2 } from 'lucide-react';

const PickerDialog = ({ open, onClose, title, items, onPick, testId }) => {
  const [q, setQ] = useState('');
  const list = useMemo(() => {
    const t = q.trim().toLowerCase();
    return items.map(i => ({ ...i, label: (i.label || '').trim() })).filter(i => !t || `${i.label} ${i.sub || ''}`.toLowerCase().includes(t))
      .sort((a, b) => a.label.localeCompare(b.label, 'es', { sensitivity: 'base' })).slice(0, 200);
  }, [items, q]);
  return (
    <Dialog open={open} onOpenChange={o => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid={testId}>
        <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar..." data-testid={`${testId}-search`}
            className="w-full h-9 pl-8 pr-2 text-sm border rounded-md outline-none focus:ring-1 focus:ring-indigo-300" />
        </div>
        <div className="max-h-80 overflow-y-auto divide-y border rounded-md">
          {list.length === 0 && <p className="text-xs text-slate-400 p-3">Sin resultados.</p>}
          {list.map(i => (
            <button key={i.id} type="button" onClick={() => { onPick(i); onClose(); }} data-testid={`${testId}-option-${i.id}`}
              className="w-full text-left px-3 py-2 text-sm hover:bg-indigo-50 flex items-center gap-2">
              <span className="font-medium text-slate-800 truncate">{i.label}</span>
              {i.sub && <span className="ml-auto text-[11px] text-slate-400 shrink-0">{i.sub}</span>}
            </button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
};

// value: {patrocinador_tipo, patrocinador_nombre}; onBank(bank) / onClient(client)
// singleRifClient: cotización de un solo RIF → «Cliente» toma ese RIF sin búsqueda.
export const SponsorTypeSelector = ({ value, banks, clients, onBank, onClient, compositeLabel, singleRifClient }) => {
  const [modal, setModal] = useState(null);
  const choose = (k) => (k === 'CLIENTE' && singleRifClient ? onClient(singleRifClient) : setModal(k));
  const opt = (k, label, Icon) => (
    <button type="button" role="radio" aria-checked={value.patrocinador_tipo === k} onClick={() => choose(k)} data-testid={`sponsor-type-${k}`}
      className={`px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors flex items-center gap-1.5 ${value.patrocinador_tipo === k ? 'bg-brand-blue-600 text-white border-brand-blue-700' : 'bg-white text-slate-700 border-slate-300 hover:border-brand-blue-400'}`}>
      <Icon size={13} /> {label}
    </button>
  );
  return (
    <div className="flex-1 min-w-0" data-testid="sponsor-type-block">
      <Label className="text-sm font-semibold text-slate-800 block mb-1">Tipo de Patrocinio <span className="text-red-500">*</span></Label>
      <p className="text-[11px] text-slate-500 mb-2">¿La cotización es Patrocinada por un Banco o por un Cliente?</p>
      <div className="flex gap-1.5 flex-wrap" role="radiogroup">
        {opt('BANCO', 'Patrocinada por Banco/Ente', Landmark)}
        {opt('CLIENTE', 'Patrocinada por Cliente', Building2)}
      </div>
      {value.patrocinador_tipo && (
        <p className="text-[11px] mt-1.5 font-medium text-emerald-700" data-testid="sponsor-selected-label">
          Patrocinador: {compositeLabel || value.patrocinador_nombre || '—'}
          {!(value.patrocinador_tipo === 'CLIENTE' && singleRifClient) && <button type="button" className="ml-2 text-indigo-600 hover:underline" onClick={() => setModal(value.patrocinador_tipo)} data-testid="sponsor-change-btn">Cambiar</button>}
          {value.patrocinador_tipo === 'CLIENTE' && singleRifClient && <span className="ml-2 text-slate-500 font-normal">(RIF único de la cotización{singleRifClient.rif ? ` · ${singleRifClient.rif}` : ''})</span>}
        </p>
      )}
      {!value.patrocinador_tipo && <p className="text-[11px] text-amber-600 mt-1.5">Debe indicar el tipo de patrocinio.</p>}
      <PickerDialog open={modal === 'BANCO'} onClose={() => setModal(null)} title="Bancos y Procesadores" testId="sponsor-bank-modal"
        items={(banks || []).map(b => ({ id: b.bank_id, label: b.name, sub: b.type || 'Banco', raw: b }))} onPick={i => onBank(i.raw)} />
      <PickerDialog open={modal === 'CLIENTE'} onClose={() => setModal(null)} title="Selección de Clientes" testId="sponsor-client-modal"
        items={(clients || []).filter(c => !c.is_branch && c.rif).map(c => ({ id: c.client_id, label: c.legal_name || c.fantasy_name, sub: c.rif, raw: c }))}
        onPick={i => onClient(i.raw)} />
    </div>
  );
};
