import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Textarea } from '../../ui/textarea';
import { Building2, User } from 'lucide-react';
import { CompanyContactsReel, emptyCompanyContact } from './CompanyContactsReel';
import { RifDocumentField } from './RifDocumentField';
import api from '../../../utils/api';
import { toast } from 'sonner';

const RIF_RE = /^[VEJGPC]-?\d{8}-?\d$/i;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const blank = { tipo_persona: 'Jurídica', razon_social: '', rif: '', direccion_fiscal: '', contacts: [emptyCompanyContact()] };

const validate = (f) => {
  if (!f.razon_social.trim()) return 'El Nombre o Razón Social es obligatorio';
  const rif = f.rif.replace(/[\s.]/g, '').toUpperCase();
  if (!RIF_RE.test(rif)) return 'RIF inválido. Formato: J-30112233-4 o V-12345678-9';
  if (f.tipo_persona === 'Natural' && !'VE'.includes(rif[0])) return 'Para Persona Natural el RIF debe iniciar con V o E';
  if (f.tipo_persona === 'Jurídica' && !'JGPC'.includes(rif[0])) return 'Para Persona Jurídica el RIF debe iniciar con J, G, P o C';
  if (!f.direccion_fiscal.trim()) return 'La Dirección Fiscal es obligatoria';
  const valid = f.contacts.filter(c => c.full_name.trim());
  if (!valid.length) return 'Debe registrar al menos un contacto corporativo';
  const bad = valid.find(c => c.email && !EMAIL_RE.test(c.email.trim()));
  return bad ? `Email inválido para el contacto ${bad.full_name}` : null;
};

const PersonaToggle = ({ value, onChange }) => (
  <div className="grid grid-cols-2 gap-2" data-testid="company-tipo-persona">
    {[['Jurídica', Building2], ['Natural', User]].map(([v, Icon]) => (
      <button key={v} type="button" onClick={() => onChange(v)} aria-pressed={value === v} data-testid={`company-tipo-${v === 'Natural' ? 'natural' : 'juridica'}`}
        className={`h-10 rounded-md border text-sm font-medium inline-flex items-center justify-center gap-2 transition-colors ${value === v ? 'bg-brand-blue-600 text-white border-brand-blue-600' : 'bg-white text-slate-600 border-slate-300 hover:border-brand-blue-400'}`}>
        <Icon size={15} /> Persona {v}
      </button>
    ))}
  </div>
);

export const CompanyFormDialog = ({ open, onOpenChange, company, onSaved }) => {
  const [form, setForm] = useState(blank);
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setFile(null);
    setForm(company ? {
      tipo_persona: company.tipo_persona || 'Jurídica', razon_social: company.razon_social || '', rif: company.rif || '',
      direccion_fiscal: company.direccion_fiscal || '',
      contacts: company.contacts?.length ? company.contacts.map(c => ({ ...emptyCompanyContact(), ...c })) : [emptyCompanyContact()],
    } : blank);
  }, [open, company]);

  const set = (patch) => setForm(prev => ({ ...prev, ...patch }));
  const save = async () => {
    const err = validate(form);
    if (err) { toast.error(err); return; }
    setSaving(true);
    try {
      const payload = { ...form, contacts: form.contacts.filter(c => c.full_name.trim()) };
      const { data } = company ? await api.put(`/integrator-companies/${company.empresa_id}`, payload) : await api.post('/integrator-companies', payload);
      if (file) {
        const fd = new FormData(); fd.append('file', file);
        await api.post(`/integrator-companies/${data.empresa_id}/rif-document`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      }
      toast.success(company ? 'Empresa Integradora actualizada' : 'Empresa Integradora creada');
      onOpenChange(false); onSaved?.(data);
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al guardar la Empresa Integradora'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="company-form-dialog">
        <DialogHeader><DialogTitle className="font-manrope text-xl">{company ? 'Ficha de la Empresa Integradora' : 'Nueva Empresa Integradora'}</DialogTitle></DialogHeader>
        {company?.ficha_incompleta && <p className="text-xs rounded-md bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2" data-testid="company-incomplete-notice">Ficha incompleta (registro migrado): complete RIF, Dirección Fiscal y al menos un contacto para guardar.</p>}
        <div className="space-y-4">
          <div><Label>Tipo de Persona *</Label><PersonaToggle value={form.tipo_persona} onChange={(v) => set({ tipo_persona: v })} /></div>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2"><Label>{form.tipo_persona === 'Natural' ? 'Nombre Completo *' : 'Razón Social *'}</Label>
              <Input maxLength={200} value={form.razon_social} onChange={e => set({ razon_social: e.target.value })} placeholder="Ej: Soluciones Tecnológicas Alpha C.A." data-testid="company-razon-social" /></div>
            <div><Label>RIF *</Label>
              <Input maxLength={20} value={form.rif} onChange={e => set({ rif: e.target.value.toUpperCase() })} placeholder={form.tipo_persona === 'Natural' ? 'V-12345678-9' : 'J-30112233-4'} data-testid="company-rif" /></div>
          </div>
          <div><Label>Dirección Fiscal *</Label>
            <Textarea rows={2} value={form.direccion_fiscal} onChange={e => set({ direccion_fiscal: e.target.value })} placeholder="Domicilio tributario completo" data-testid="company-direccion" /></div>
          <RifDocumentField empresaId={company?.empresa_id} filename={company?.rif_document_filename} pendingFile={file} onPick={setFile} />
          <CompanyContactsReel contacts={form.contacts} onChange={(contacts) => set({ contacts })} />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} data-testid="company-cancel-btn">Cancelar</Button>
          <Button onClick={save} disabled={saving} className="bg-brand-green-600 hover:bg-brand-green-700" data-testid="company-save-btn">{saving ? 'Guardando...' : 'Guardar'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
