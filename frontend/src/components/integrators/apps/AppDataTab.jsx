import { useEffect, useState } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Textarea } from '../../ui/textarea';
import { Label } from '../../ui/label';
import { Pencil } from 'lucide-react';
import { ReasonField, reasonError } from './ReasonField';
import { ImplementerField } from './ImplementerField';
import { buildPayload, INTEGRATION_TYPES, INTEGRATION_MODALITIES, PHASES } from './appPayload';
import api from '../../../utils/api';
import { toast } from 'sonner';

const FIELDS = [
  ['app_name', 'Nombre del Aplicativo', 'text'], ['integration_type', 'Tipo de Integración', INTEGRATION_TYPES],
  ['integration_modality', 'Modalidad / Protocolo', INTEGRATION_MODALITIES], ['integration_phase', 'Fase', PHASES],
  ['componente_version', 'Componente / Versión', 'text'], ['gestor', 'Gestor', 'text'], ['categoria', 'Categoría', 'text'],
  ['ticket_number', 'Ticket', 'text'], ['comercios_relacionados', 'Comercios Relacionados', 'text'],
  ['productos_certificar', 'Productos a Certificar', 'text'], ['principal_contact_name', 'Contacto Principal', 'text'],
  ['principal_contact_phone', 'Teléfono Contacto Principal', 'text'], ['principal_contact_email', 'Email Contacto Principal', 'text'],
  ['observations', 'Observaciones', 'area'],
];
const READ_ONLY = [['integrator_type', 'Tipo de Integrador'], ['integrator_status', 'Estatus'],
  ['coordinador', 'Coordinador'], ['cert_component', 'Componente Certificado'], ['cert_version', 'Versión Certificada'],
  ['certified_at', 'Fecha de Certificación'], ['certified_by', 'Certificado por']];

const fmt = (k, v) => (k === 'certified_at' && v ? new Date(v).toLocaleDateString('es-VE') : v) || '—';

const FieldInput = ({ k, kind, value, onChange }) => {
  const common = { value: value || '', onChange: (e) => onChange(e.target.value), 'data-testid': `app-field-${k}` };
  if (kind === 'area') return <Textarea rows={2} className="text-sm" {...common} />;
  if (Array.isArray(kind)) return (
    <select className="h-9 w-full rounded-md border border-input bg-white px-2 text-sm" {...common}>
      <option value="">—</option>{[...new Set([...(value ? [value] : []), ...kind])].map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  );
  return <Input className="h-9 text-sm" {...common} />;
};

export const AppDataTab = ({ app, editable, locked, isAdmin, onSaved }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({});
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => { setEditing(false); setReason(''); }, [app]);

  const start = () => { setDraft(Object.fromEntries(FIELDS.map(([k]) => [k, app[k] || '']))); setReason(''); setEditing(true); };
  const save = async () => {
    const err = reasonError(locked, reason);
    if (err) { toast.error(err); return; }
    if (!draft.app_name?.trim()) { toast.error('El Nombre del Aplicativo es obligatorio'); return; }
    setSaving(true);
    try {
      const patch = Object.fromEntries(Object.entries(draft).map(([k, v]) => [k, (v || '').trim() || null]));
      await api.put(`/integrators/${app.integrator_id}`, buildPayload(app, { ...patch, app_name: draft.app_name.trim(), change_reason: reason.trim() || null }));
      toast.success('Datos técnicos actualizados'); setEditing(false); onSaved();
    } catch (e) { toast.error(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Error al guardar los datos'); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-4" data-testid="app-data-tab">
      <div className="flex justify-end">
        {editable && !editing && <Button size="sm" variant="outline" onClick={start} data-testid="app-data-edit-btn"><Pencil size={13} className="mr-1" />Editar datos técnicos</Button>}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-3">
        {FIELDS.map(([k, label, kind]) => (
          <div key={k} className={kind === 'area' ? 'col-span-2 md:col-span-3' : ''}>
            <Label className="text-[11px] uppercase tracking-wide text-slate-400">{label}</Label>
            {editing ? <FieldInput k={k} kind={kind} value={draft[k]} onChange={(v) => setDraft((d) => ({ ...d, [k]: v }))} />
              : <p className="text-sm text-slate-800 whitespace-pre-wrap break-words" data-testid={`app-value-${k}`}>{app[k] || '—'}</p>}
          </div>
        ))}
        <ImplementerField app={app} isAdmin={isAdmin} onSaved={onSaved} />
        {READ_ONLY.map(([k, label]) => (
          <div key={k}><Label className="text-[11px] uppercase tracking-wide text-slate-400">{label}</Label>
            <p className="text-sm text-slate-600" data-testid={`app-value-${k}`}>{fmt(k, app[k])}</p></div>
        ))}
      </div>
      {editing && (
        <div className="space-y-3 border-t pt-3">
          {locked && <ReasonField value={reason} onChange={setReason} testId="app-data-reason" />}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setEditing(false)} data-testid="app-data-cancel-btn">Cancelar</Button>
            <Button size="sm" disabled={saving} onClick={save} className="bg-brand-green-600 hover:bg-brand-green-700" data-testid="app-data-save-btn">{saving ? 'Guardando...' : 'Guardar cambios'}</Button>
          </div>
        </div>
      )}
    </div>
  );
};
