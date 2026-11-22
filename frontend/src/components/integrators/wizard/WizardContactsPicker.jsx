import { useEffect, useMemo, useState } from 'react';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { Search, UserPlus, X, Check, Star } from 'lucide-react';
import api from '../../../utils/api';
import { ContactRoleSelect } from '../ContactRoleSelect';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const keyOf = (c) => (c.email || '').trim().toLowerCase() || (c.name || '').trim().toLowerCase();
const newRow = () => ({ contact_id: `ctc_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`, name: '', email: '', phone: '', role: '', _new: true });

const EcosystemList = ({ items, selectedKeys, onToggle }) => {
  const [q, setQ] = useState('');
  const shown = useMemo(() => {
    const s = q.trim().toLowerCase();
    return items.filter((c) => !s || `${c.name} ${c.email} ${c.role} ${c.source}`.toLowerCase().includes(s));
  }, [items, q]);
  return (
    <div className="rounded-md border border-slate-200 bg-white" data-testid="wizard-ecosystem-list">
      <div className="relative border-b border-slate-100">
        <Search size={13} className="absolute left-2.5 top-2.5 text-slate-400" />
        <input className="w-full h-8 pl-8 pr-2 text-xs outline-none rounded-t-md" placeholder={`Buscar entre ${items.length} contactos del integrador...`} value={q} onChange={(e) => setQ(e.target.value)} data-testid="wizard-ecosystem-search" />
      </div>
      <div className="max-h-44 overflow-y-auto divide-y divide-slate-50">
        {shown.map((c, i) => {
          const on = selectedKeys.has(keyOf(c));
          return (
            <button key={i} type="button" onClick={() => onToggle(c)} data-testid={`wizard-ecosystem-contact-${i}`}
              className={`w-full flex items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors ${on ? 'bg-emerald-50' : 'hover:bg-slate-50'}`}>
              <span className={`h-4 w-4 rounded border flex items-center justify-center shrink-0 ${on ? 'bg-emerald-600 border-emerald-600 text-white' : 'border-slate-300'}`}>{on && <Check size={11} />}</span>
              <span className="font-semibold text-slate-800">{c.name}</span>
              <span className="text-slate-500 truncate">{c.email}{c.phone ? ` · ${c.phone}` : ''}</span>
              <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 whitespace-nowrap">{c.source}</span>
            </button>
          );
        })}
        {!shown.length && <p className="px-3 py-2 text-[11px] text-slate-400">Sin coincidencias</p>}
      </div>
    </div>
  );
};

export const WizardContactsPicker = ({ empresaId, contacts, onChange, required }) => {
  const [eco, setEco] = useState([]);
  useEffect(() => {
    if (!empresaId) { setEco([]); return; }
    api.get('/integrator-companies/ecosystem-contacts', { params: { empresa_id: empresaId } }).then((r) => setEco(r.data || [])).catch(() => setEco([]));
  }, [empresaId]);
  const list = contacts || [];
  useEffect(() => { if (required && list.length === 0) onChange([newRow()]); }, [required, list.length]); // eslint-disable-line react-hooks/exhaustive-deps
  const selectedKeys = useMemo(() => new Set(list.filter((c) => !c._new).map(keyOf)), [list]);

  const toggle = (c) => {
    const k = keyOf(c);
    if (selectedKeys.has(k)) onChange(list.filter((x) => x._new || keyOf(x) !== k));
    else onChange([...list, { contact_id: `ctc_${Date.now().toString(36)}`, name: c.name, email: c.email, phone: c.phone, role: c.role }]);
  };
  const update = (idx, patch) => onChange(list.map((c, i) => (i === idx ? { ...c, ...patch } : c)));

  return (
    <div className="border-t border-slate-200 pt-3 mt-3 space-y-2" data-testid="wizard-responsible-block">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-brand-blue-600 uppercase tracking-wider">
          Contactos del Integrador {required ? '*' : <span className="text-slate-400 normal-case font-normal">(opcional)</span>}
        </p>
        <Button type="button" size="sm" variant="outline" className="h-7 text-xs" onClick={() => onChange([...list, newRow()])} data-testid="wizard-add-new-contact-btn"><UserPlus size={13} className="mr-1" />Registrar contacto nuevo</Button>
      </div>
      {eco.length > 0 && <EcosystemList items={eco} selectedKeys={selectedKeys} onToggle={toggle} />}
      {list.length === 0 && <p className="text-[11px] text-slate-400" data-testid="wizard-contacts-empty">{eco.length ? 'Selecciona uno o varios contactos de la lista o registra uno nuevo.' : 'Registra el contacto responsable del integrador.'}</p>}
      <div className="space-y-1.5" data-testid="wizard-selected-contacts">
        {list.map((c, idx) => (
          <div key={c.contact_id || idx} className="grid grid-cols-12 gap-2 items-center rounded-md border border-slate-200 bg-slate-50 p-2" data-testid={`wizard-contact-row-${idx}`}>
            <span className="col-span-1 flex justify-center" title={idx === 0 ? 'Responsable principal' : ''}>{idx === 0 ? <Star size={14} className="text-amber-500 fill-amber-400" /> : <span className="text-[10px] text-slate-400">{idx + 1}</span>}</span>
            {c._new ? (<>
              <Input className="col-span-3 h-8 text-xs bg-white" placeholder={`Nombre${required && idx === 0 ? ' *' : ''}`} value={c.name} onChange={(e) => update(idx, { name: e.target.value })} data-testid={`wizard-resp-name${idx ? `-${idx}` : ''}`} />
              <Input className={`col-span-3 h-8 text-xs bg-white ${c.email && !EMAIL_RE.test(c.email.trim()) ? 'border-red-400' : ''}`} placeholder="Email" value={c.email} onChange={(e) => update(idx, { email: e.target.value })} data-testid={`wizard-resp-email${idx ? `-${idx}` : ''}`} />
              <Input className="col-span-2 h-8 text-xs bg-white" placeholder="Teléfono" value={c.phone} onChange={(e) => update(idx, { phone: e.target.value })} data-testid={`wizard-resp-phone${idx ? `-${idx}` : ''}`} />
              <ContactRoleSelect className="col-span-2 h-8" value={c.role} onChange={(v) => update(idx, { role: v })} testId={`wizard-resp-role${idx ? `-${idx}` : ''}`} />
            </>) : (
              <div className="col-span-10 text-xs"><span className="font-semibold text-slate-800">{c.name}</span> <span className="text-slate-500">{c.email}{c.phone ? ` · ${c.phone}` : ''}</span>{c.role && <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded bg-cyan-50 text-cyan-700">{c.role}</span>}</div>
            )}
            <button type="button" className="col-span-1 text-red-400 hover:text-red-600 flex justify-center" onClick={() => onChange(list.filter((_, i) => i !== idx))} data-testid={`wizard-contact-remove-${idx}`}><X size={14} /></button>
          </div>
        ))}
      </div>
      {list.length > 0 && <p className="text-[10px] text-slate-400">★ El primero queda como Responsable principal. Los contactos nuevos también se agregan al Reel Corporativo de la empresa.</p>}
    </div>
  );
};

export const newContactsOf = (contacts) => (contacts || []).filter((c) => c._new && (c.name || '').trim())
  .map((c) => ({ full_name: c.name.trim(), email: (c.email || '').trim(), phone: (c.phone || '').trim(), role: (c.role || '').trim() }));
export const cleanWizardContacts = (contacts) => (contacts || []).filter((c) => (c.name || c.email || c.phone || '').trim())
  .map(({ _new, ...c }) => c);
