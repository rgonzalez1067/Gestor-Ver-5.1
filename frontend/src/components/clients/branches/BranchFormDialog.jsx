import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import api from '../../../utils/api';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Textarea } from '../../ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../ui/dialog';
import { Plus, Trash2, Link2, Store, Check, Circle } from 'lucide-react';
import { CONTACT_PURPOSES } from '../../../utils/contactPurposes';

const ROLES = ['Administrativo', 'Financiero', 'Técnico', 'Cuentas por Pagar', 'Operativo', 'Propietario', 'Director', 'Integrador'];
const blank = () => ({ contact_id: '', full_name: '', role: 'Administrativo', phone: '', email: '', purposes: [] });

const PurposeTags = ({ c, i, onChange }) => (
  <div className="col-span-12 flex flex-wrap items-center gap-1.5" data-testid={`branch-contact-purposes-${i}`}>
    <span className="text-[11px] font-semibold text-slate-500 mr-1">Procesos:</span>
    {CONTACT_PURPOSES.map(p => {
      const active = (c.purposes || []).includes(p.key);
      return (
        <button key={p.key} type="button" aria-pressed={active} data-testid={`branch-contact-purpose-${i}-${p.key}`}
          onClick={() => onChange({ ...c, purposes: active ? c.purposes.filter(k => k !== p.key) : [...(c.purposes || []), p.key] })}
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border transition-colors ${active ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400'}`}>
          {active ? <Check size={11} /> : <Circle size={10} className="opacity-50" />}{p.label}
        </button>
      );
    })}
  </div>
);

const ContactRow = ({ c, i, onChange, onRemove }) => (
  <div className="grid grid-cols-12 gap-2 items-center rounded-md border border-slate-200 p-2" data-testid={`branch-contact-row-${i}`}>
    <Input className="col-span-3 h-8 text-sm" placeholder="Nombre" value={c.full_name} onChange={(e) => onChange({ ...c, full_name: e.target.value })} data-testid={`branch-contact-name-${i}`} />
    <Input className="col-span-3 h-8 text-sm" placeholder="Teléfono" value={c.phone} onChange={(e) => onChange({ ...c, phone: e.target.value })} data-testid={`branch-contact-phone-${i}`} />
    <Input className="col-span-3 h-8 text-sm" placeholder="Email" type="email" value={c.email} onChange={(e) => onChange({ ...c, email: e.target.value })} data-testid={`branch-contact-email-${i}`} />
    <select className="col-span-2 h-8 text-sm border rounded-md px-1 bg-white" value={c.role || 'Administrativo'} onChange={(e) => onChange({ ...c, role: e.target.value })} data-testid={`branch-contact-role-${i}`}>
      {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
    </select>
    <button type="button" onClick={onRemove} className="col-span-1 text-slate-400 hover:text-red-600 justify-self-center" data-testid={`branch-contact-remove-${i}`}><Trash2 size={14} /></button>
    <PurposeTags c={c} i={i} onChange={onChange} />
  </div>
);

const InheritedContacts = ({ contacts }) => (
  <div className="rounded-md border border-dashed border-sky-300 bg-sky-50 p-2.5 text-xs text-sky-800" data-testid="branch-inherited-contacts">
    <p className="font-semibold flex items-center gap-1 mb-1"><Link2 size={12} /> Sin contactos propios — se usan los Heredados del RIF</p>
    {contacts.length ? contacts.map((c, i) => <p key={i}>{c.full_name || '—'} · {c.phone || 'sin teléfono'} · {c.email || 'sin correo'} · {c.role || ''}</p>)
      : <p>El RIF no tiene contactos; se heredan de la Marca / Grupo Económico.</p>}
  </div>
);

// Alta / edición de una sucursal desde la ficha del RIF.
export const BranchFormDialog = ({ open, onOpenChange, principal, branch, principalContacts = [], onSaved }) => {
  const [form, setForm] = useState({ sucursal: '', branch_address: '', cantidad_cajas: '', contacts: [] });
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (!open) return;
    setForm(branch
      ? { sucursal: branch.sucursal || '', branch_address: branch.branch_address || '', cantidad_cajas: branch.cantidad_cajas ?? '', contacts: (branch.contacts || []).map(c => ({ ...blank(), ...c, purposes: Array.isArray(c.purposes) ? c.purposes : [] })) }
      : { sucursal: '', branch_address: '', cantidad_cajas: '', contacts: [] });
  }, [open, branch]);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const contacts = form.contacts;

  const save = async () => {
    const name = form.sucursal.trim();
    if (!name || name.toLowerCase() === 'principal') return toast.error("Indique un nombre de sucursal distinto de 'Principal'");
    if (!form.branch_address.trim()) return toast.error('La dirección física es obligatoria');
    if (!(parseInt(form.cantidad_cajas, 10) >= 1)) return toast.error('La cantidad de cajas debe ser mayor o igual a 1');
    const payload = { sucursal: name, branch_address: form.branch_address.trim(), cantidad_cajas: parseInt(form.cantidad_cajas, 10),
      contacts: contacts.filter(c => (c.full_name || '').trim() || (c.email || '').trim() || (c.phone || '').trim()) };
    setSaving(true);
    try {
      if (branch) await api.put(`/clients/${branch.client_id}/branch-data`, payload);
      else await api.post(`/clients/${principal.client_id}/branches`, payload);
      toast.success(branch ? 'Sucursal actualizada' : 'Sucursal agregada al RIF');
      onOpenChange(false);
      onSaved?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al guardar la sucursal');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl" data-testid="branch-form-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Store size={18} className="text-amber-600" />{branch ? 'Editar Sucursal' : 'Agregar Sucursal'}
            <span className="text-sm font-normal text-slate-500">· {principal?.rif} — {principal?.legal_name}</span></DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-4 gap-3">
          <div className="col-span-3">
            <Label className="text-xs">Nombre de la Sucursal <span className="text-red-500">*</span></Label>
            <Input maxLength={150} value={form.sucursal} onChange={(e) => set('sucursal', e.target.value)} placeholder="Ej: Sucursal Altamira" data-testid="branch-form-name" />
          </div>
          <div>
            <Label className="text-xs">Cantidad de Cajas <span className="text-red-500">*</span></Label>
            <Input type="number" min="1" value={form.cantidad_cajas} onChange={(e) => set('cantidad_cajas', e.target.value)} data-testid="branch-form-cajas" />
          </div>
          <div className="col-span-4">
            <Label className="text-xs">Dirección Física <span className="text-red-500">*</span></Label>
            <Textarea rows={2} value={form.branch_address} onChange={(e) => set('branch_address', e.target.value)} placeholder="Ubicación de operación o despacho de equipos" data-testid="branch-form-address" />
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-semibold">Contactos de la Sucursal (opcional)</Label>
            <Button type="button" size="sm" variant="outline" onClick={() => set('contacts', [...contacts, blank()])} data-testid="branch-form-add-contact"><Plus size={13} className="mr-1" />Contacto</Button>
          </div>
          {contacts.map((c, i) => (
            <ContactRow key={i} c={c} i={i} onChange={(nc) => set('contacts', contacts.map((x, j) => (j === i ? nc : x)))}
              onRemove={() => set('contacts', contacts.filter((_, j) => j !== i))} />
          ))}
          {!contacts.some(c => (c.full_name || c.email || '').trim()) && <InheritedContacts contacts={principalContacts} />}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="branch-form-cancel">Cancelar</Button>
          <Button onClick={save} disabled={saving} className="bg-amber-600 hover:bg-amber-700" data-testid="branch-form-save">{saving ? 'Guardando…' : 'Guardar Sucursal'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
