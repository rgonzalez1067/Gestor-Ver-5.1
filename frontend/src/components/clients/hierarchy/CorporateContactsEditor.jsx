import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Plus, X, Check, Circle, Contact as ContactIcon } from 'lucide-react';
import { CONTACT_PURPOSES } from '../../../utils/contactPurposes';

const ROLES = ['Administrativo', 'Financiero', 'Técnico', 'Cuentas por Pagar', 'Operativo', 'Propietario', 'Director', 'Integrador'];
export const emptyCorporateContact = () => ({ contact_id: '', full_name: '', phone: '', email: '', role: 'Administrativo', purposes: [] });

export const CorporateContactsEditor = ({ contacts, onChange, editable, title = 'Contactos', testPrefix = 'group-contact', addTestId = 'add-group-contact-btn' }) => {
  const update = (idx, patch) => onChange(contacts.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
  const togglePurpose = (idx, key) => {
    const cur = Array.isArray(contacts[idx].purposes) ? contacts[idx].purposes : [];
    update(idx, { purposes: cur.includes(key) ? cur.filter(x => x !== key) : [...cur, key] });
  };
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5"><ContactIcon size={15} /> {title}</h3>
        {editable && <Button size="sm" variant="outline" onClick={() => onChange([...contacts, emptyCorporateContact()])} data-testid={addTestId}><Plus size={14} className="mr-1" /> Agregar</Button>}
      </div>
      {contacts.length === 0 && <p className="text-xs text-slate-400">Sin contactos propios.</p>}
      <div className="space-y-3">
        {contacts.map((c, idx) => (
          <div key={idx} className="grid grid-cols-12 gap-2 border border-slate-200 p-3 rounded-lg" data-testid={`${testPrefix}-${idx}`}>
            <Input className="col-span-3" placeholder="Nombre completo" value={c.full_name} onChange={e => update(idx, { full_name: e.target.value })} disabled={!editable} data-testid={`${testPrefix}-name-${idx}`} />
            <Input className="col-span-3" placeholder="Email" value={c.email} onChange={e => update(idx, { email: e.target.value })} disabled={!editable} data-testid={`${testPrefix}-email-${idx}`} />
            <Input className="col-span-2" placeholder="Teléfono" value={c.phone} onChange={e => update(idx, { phone: e.target.value })} disabled={!editable} data-testid={`${testPrefix}-phone-${idx}`} />
            <div className="col-span-3">
              <Select value={c.role} onValueChange={v => update(idx, { role: v })} disabled={!editable}>
                <SelectTrigger data-testid={`${testPrefix}-role-${idx}`}><SelectValue /></SelectTrigger>
                <SelectContent>{ROLES.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            {editable && <Button size="sm" variant="ghost" className="col-span-1 h-8 w-8 p-0 text-red-500" onClick={() => onChange(contacts.filter((_, i) => i !== idx))} data-testid={`${testPrefix}-remove-${idx}`}><X size={15} /></Button>}
            <div className="col-span-12">
              <p className="text-[11px] font-semibold text-slate-500 mb-1.5">Perfilamiento de Procesos</p>
              <div className="flex flex-wrap gap-1.5" data-testid={`${testPrefix}-purposes-${idx}`}>
                {CONTACT_PURPOSES.map(p => {
                  const active = Array.isArray(c.purposes) && c.purposes.includes(p.key);
                  return (
                    <button key={p.key} type="button" disabled={!editable} onClick={() => togglePurpose(idx, p.key)}
                      aria-pressed={active} data-testid={`${testPrefix}-purpose-${idx}-${p.key}`}
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${active ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400'}`}>
                      {active ? <Check size={12} /> : <Circle size={11} className="opacity-50" />}
                      {p.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
