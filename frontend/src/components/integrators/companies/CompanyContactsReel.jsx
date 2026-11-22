import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { Plus, X, Contact as ContactIcon } from 'lucide-react';

const ROLES = ['Director', 'Gerente General', 'Líder Técnico', 'Administrativo', 'Comercial', 'Contacto Principal', 'Soporte'];
export const emptyCompanyContact = () => ({ contact_id: '', full_name: '', phone: '', email: '', role: '' });

export const CompanyContactsReel = ({ contacts, onChange }) => {
  const update = (idx, patch) => onChange(contacts.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
  return (
    <div data-testid="company-contacts-reel">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
          <ContactIcon size={15} /> Reel de Contactos Corporativos <span className="text-red-500">*</span>
          <span className="text-[11px] font-normal text-slate-400">(mínimo 1)</span>
        </h3>
        <Button type="button" size="sm" variant="outline" onClick={() => onChange([...contacts, emptyCompanyContact()])} data-testid="company-add-contact-btn">
          <Plus size={14} className="mr-1" /> Agregar Contacto
        </Button>
      </div>
      <datalist id="company-contact-roles">{ROLES.map(r => <option key={r} value={r} />)}</datalist>
      {contacts.length === 0 && <p className="text-xs text-slate-400" data-testid="company-contacts-empty">Sin contactos registrados.</p>}
      <div className="space-y-2">
        {contacts.map((c, idx) => (
          <div key={idx} className="grid grid-cols-12 gap-2 border border-slate-200 p-2 rounded-lg bg-slate-50/60" data-testid={`company-contact-${idx}`}>
            <Input className="col-span-3 h-9" placeholder="Nombre *" value={c.full_name} onChange={e => update(idx, { full_name: e.target.value })} data-testid={`company-contact-name-${idx}`} />
            <Input className="col-span-2 h-9" placeholder="Teléfono" value={c.phone} onChange={e => update(idx, { phone: e.target.value })} data-testid={`company-contact-phone-${idx}`} />
            <Input className="col-span-3 h-9" placeholder="Email" value={c.email} onChange={e => update(idx, { email: e.target.value })} data-testid={`company-contact-email-${idx}`} />
            <Input className="col-span-3 h-9" placeholder="Rol en la empresa" list="company-contact-roles" value={c.role} onChange={e => update(idx, { role: e.target.value })} data-testid={`company-contact-role-${idx}`} />
            <Button type="button" size="sm" variant="ghost" className="col-span-1 h-9 w-9 p-0 text-red-500" onClick={() => onChange(contacts.filter((_, i) => i !== idx))} data-testid={`company-contact-remove-${idx}`}><X size={15} /></Button>
          </div>
        ))}
      </div>
    </div>
  );
};
