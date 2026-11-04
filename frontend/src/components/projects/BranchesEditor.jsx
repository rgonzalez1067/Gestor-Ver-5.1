import React, { useMemo, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../ui/select';
import { Plus, Trash2, Store, Lock, Replace } from 'lucide-react';

const keyOf = (bank, prod) => `${(bank || '').trim()}|${(prod || '').trim()}`;
const splitKey = (k) => { const [bank_name, ...rest] = k.split('|'); return { bank_name, product_name: rest.join('|') }; };
const slug = (s) => (s || '').trim().replace(/\s+/g, '-').toLowerCase();
const slugKey = (k) => `${slug(splitKey(k).bank_name)}--${slug(splitKey(k).product_name)}`;
const normBank = (n) => (n || '').replace(/\s*\([^)]*\)\s*$/, '').trim().toLowerCase();

const FLAG = { VPOS: 'vpos_available', MPOS: 'mpos_available', GATEWAY: 'gateway_available', LINK: 'link_available' };

// Agrupa cada medio con el medio cotizado cuyo tope comparte.
export const useBranchUsage = (branches, baseline, replacements) => useMemo(() => {
  const caps = baseline?.medios || {};
  const groupOf = Object.fromEntries(Object.keys(caps).map(k => [k, k]));
  replacements.forEach(r => {
    const from = keyOf(r.bank_name, r.from_product);
    const to = keyOf(r.bank_name, r.to_product);
    if (caps[from] !== undefined && caps[to] === undefined) groupOf[to] = groupOf[from];
  });
  const used = {};
  branches.forEach(b => b.medios.forEach(m => {
    const g = groupOf[keyOf(m.bank_name, m.product_name)];
    if (g) used[g] = (used[g] || 0) + (parseInt(b.box_count) || 0);
  }));
  const total = branches.reduce((a, b) => a + (parseInt(b.box_count) || 0), 0);
  return { caps, groupOf, used, total, options: Object.keys(groupOf) };
}, [branches, baseline, replacements]);

const ReplacementsPanel = ({ caps, replacements, onChange, banksCatalog, quoteType }) => {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const fromObj = from ? splitKey(from) : null;
  const candidates = useMemo(() => {
    if (!fromObj) return [];
    const bank = banksCatalog.find(b => b.name === fromObj.bank_name) || banksCatalog.find(b => normBank(b.name) === normBank(fromObj.bank_name));
    const flag = FLAG[(quoteType || 'VPOS').toUpperCase()] || 'vpos_available';
    return (bank?.products || []).filter(p => p[flag] && caps[keyOf(fromObj.bank_name, p.product_name)] === undefined).map(p => p.product_name);
  }, [fromObj, banksCatalog, quoteType, caps]);

  const add = () => {
    if (!fromObj || !to) return;
    onChange([...replacements, { bank_name: fromObj.bank_name, from_product: fromObj.product_name, to_product: to }]);
    setFrom(''); setTo('');
  };

  return (
    <div className="rounded-lg border border-violet-200 bg-violet-50/40 p-3 space-y-2" data-testid="master-replacements-panel">
      <p className="text-xs font-semibold text-violet-800 flex items-center gap-1.5"><Replace size={13} />Reemplazo de medio de pago</p>
      <p className="text-[11px] text-violet-700/80">El medio nuevo hereda el tope de cajas del medio cotizado que reemplaza (ambos comparten ese tope).</p>
      {replacements.map((r, i) => (
        <div key={i} className="flex items-center gap-2 text-xs bg-white rounded border border-violet-100 px-2 py-1" data-testid={`master-replacement-${i}`}>
          <span className="flex-1 truncate">{r.bank_name}: <b>{r.from_product}</b> → <b>{r.to_product}</b></span>
          <button type="button" onClick={() => onChange(replacements.filter((_, j) => j !== i))} className="text-rose-500" data-testid={`master-replacement-remove-${i}`}><Trash2 size={13} /></button>
        </div>
      ))}
      <div className="flex gap-2" key={replacements.length}>
        <Select value={from || undefined} onValueChange={(v) => { setFrom(v); setTo(''); }}>
          <SelectTrigger className="h-8 text-xs bg-white flex-1" data-testid="master-replacement-from"><SelectValue placeholder="Medio cotizado..." /></SelectTrigger>
          <SelectContent>{Object.keys(caps).map(k => <SelectItem key={k} value={k}>{splitKey(k).product_name} · {splitKey(k).bank_name}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={to || undefined} onValueChange={setTo} disabled={!from}>
          <SelectTrigger className="h-8 text-xs bg-white flex-1" data-testid="master-replacement-to"><SelectValue placeholder={from && !candidates.length ? 'Sin alternativas' : 'Reemplazar por...'} /></SelectTrigger>
          <SelectContent>{candidates.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
        </Select>
        <Button type="button" size="sm" variant="outline" onClick={add} disabled={!from || !to} className="h-8 text-violet-700 border-violet-300" data-testid="master-replacement-add">Agregar</Button>
      </div>
    </div>
  );
};

const BranchCard = ({ b, idx, certified, clients, options, onPatch, onRemove }) => {
  const toggle = (k) => {
    const has = b.medios.some(m => keyOf(m.bank_name, m.product_name) === k);
    if (certified && has) return;
    onPatch({ medios: has ? b.medios.filter(m => keyOf(m.bank_name, m.product_name) !== k) : [...b.medios, splitKey(k)] });
  };
  // Medios de la sucursal fuera del alcance contratado (legacy o reemplazo quitado): visibles para poder quitarlos.
  const invalid = b.medios.map(m => keyOf(m.bank_name, m.product_name)).filter(k => !options.includes(k));
  return (
    <div className="rounded-lg border border-slate-200 p-3 bg-slate-50/60 space-y-2" data-testid={`master-branch-${idx}`}>
      <div className="grid grid-cols-12 gap-2 items-end">
        <div className="col-span-4">
          <Label className="text-[11px]">Sucursal</Label>
          <Input value={b.name} onChange={e => onPatch({ name: e.target.value })} className="h-8 text-sm bg-white" data-testid={`master-branch-name-${idx}`} />
        </div>
        <div className="col-span-5">
          <Label className="text-[11px]">RIF</Label>
          <Select value={b.client_id || undefined} onValueChange={v => onPatch({ client_id: v })}>
            <SelectTrigger className="h-8 text-xs bg-white" data-testid={`master-branch-rif-${idx}`}><SelectValue placeholder="Seleccionar RIF..." /></SelectTrigger>
            <SelectContent>{clients.map(c => <SelectItem key={c.client_id} value={c.client_id}>{c.rif || 'sin RIF'} · {c.legal_name || c.fantasy_name}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="col-span-2">
          <Label className="text-[11px]">Cajas</Label>
          <Input type="number" min="0" value={b.box_count} onChange={e => onPatch({ box_count: e.target.value })} disabled={certified}
            title={certified ? 'Sucursal certificada: cajas bloqueadas' : undefined}
            className="h-8 text-sm bg-white" data-testid={`master-branch-boxes-${idx}`} />
        </div>
        <div className="col-span-1 flex justify-end">
          <Button type="button" size="sm" variant="ghost" onClick={onRemove} disabled={certified}
            title={certified ? 'Sucursal certificada: no se puede eliminar' : 'Eliminar sucursal'}
            className="h-8 px-2 text-rose-500 hover:bg-rose-50" data-testid={`master-branch-remove-${idx}`}>
            {certified ? <Lock size={14} className="text-slate-400" /> : <Trash2 size={14} />}
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 pl-1">
        {options.map(k => (
          <label key={k} className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
            <Checkbox checked={b.medios.some(m => keyOf(m.bank_name, m.product_name) === k)} onCheckedChange={() => toggle(k)}
              data-testid={`master-branch-medio-${idx}-${slugKey(k)}`} />
            <span className="truncate">{splitKey(k).product_name} <span className="text-slate-400">· {splitKey(k).bank_name}</span></span>
          </label>
        ))}
        {invalid.map(k => (
          <label key={k} className="flex items-center gap-2 text-xs text-rose-700 cursor-pointer" title="No contratado: desmárcalo para poder guardar">
            <Checkbox checked onCheckedChange={() => onPatch({ medios: b.medios.filter(m => keyOf(m.bank_name, m.product_name) !== k) })}
              data-testid={`master-branch-medio-invalid-${idx}-${slugKey(k)}`} />
            <span className="truncate line-through">{splitKey(k).product_name} <span className="text-rose-400">· {splitKey(k).bank_name} · no contratado</span></span>
          </label>
        ))}
      </div>
    </div>
  );
};

export const BranchesEditor = ({ branches, onChange, context, replacements, onReplacementsChange, banksCatalog, quoteType, defaultClientId = '' }) => {
  const { caps, groupOf, used, total, options } = useBranchUsage(branches, context?.baseline, replacements);
  const cap = context?.baseline?.total_boxes || 0;
  const certified = new Set(context?.certified_store_ids || []);
  const clients = context?.eligible_clients || [];
  const patch = (i, p) => onChange(branches.map((b, j) => (j === i ? { ...b, ...p } : b)));

  return (
    <div className="space-y-3" data-testid="master-branches-editor">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className={`px-2 py-1 rounded border font-semibold ${total > cap ? 'bg-rose-50 border-rose-300 text-rose-700' : 'bg-emerald-50 border-emerald-200 text-emerald-700'}`} data-testid="master-branches-total">
          Cajas asignadas {total} / {cap} contratadas
        </span>
        {Object.keys(caps).map(g => (
          <span key={g} className={`px-2 py-1 rounded border ${(used[g] || 0) > caps[g] ? 'bg-rose-50 border-rose-300 text-rose-700' : 'bg-white border-slate-200 text-slate-600'}`} data-testid={`master-medio-usage-${slugKey(g)}`}>
            {splitKey(g).product_name} <span className="text-slate-400">({splitKey(g).bank_name})</span>: {used[g] || 0}/{caps[g]}
            {options.filter(k => k !== g && groupOf[k] === g).map(k => <span key={k} className="text-violet-600"> + {splitKey(k).product_name}</span>)}
          </span>
        ))}
      </div>
      {branches.map((b, i) => (
        <BranchCard key={b.store_id || `new-${i}`} b={b} idx={i} certified={b.store_id && certified.has(b.store_id)}
          clients={clients} options={options} onPatch={(p) => patch(i, p)} onRemove={() => onChange(branches.filter((_, j) => j !== i))} />
      ))}
      <Button type="button" size="sm" variant="outline" onClick={() => onChange([...branches, { store_id: null, name: '', client_id: defaultClientId, box_count: 0, medios: [] }])}
        className="text-indigo-600 border-indigo-200 hover:bg-indigo-50" data-testid="master-add-branch">
        <Plus size={14} className="mr-1" /><Store size={13} className="mr-1" />Agregar Sucursal
      </Button>
      <ReplacementsPanel caps={caps} replacements={replacements} onChange={onReplacementsChange} banksCatalog={banksCatalog} quoteType={quoteType} />
    </div>
  );
};
