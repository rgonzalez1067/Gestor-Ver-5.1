import { useEffect, useState } from 'react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Plus, X, Wrench, UserPlus } from 'lucide-react';
import api from '../../utils/api';
import { ContactRoleSelect } from '../integrators/ContactRoleSelect';
export const emptyTechnician = () => ({ tech_id: '', name: '', phone: '', email: '', role: '' });

export const useTechnicianSuggestions = (integratorId) => {
  const [list, setList] = useState([]);
  useEffect(() => {
    if (!integratorId || integratorId === 'sin_integrador') { setList([]); return; }
    api.get('/integrator-companies/technicians', { params: { integrator_id: integratorId } }).then(r => setList(r.data || [])).catch(() => setList([]));
  }, [integratorId]);
  return list;
};

export const IntegrationTechniciansReel = ({ value, onChange, integratorId, testPrefix = 'tech' }) => {
  const suggestions = useTechnicianSuggestions(integratorId);
  const techs = value || [];
  const key = (t) => (t.email || '').trim().toLowerCase() || (t.name || '').trim().toLowerCase();
  const used = new Set(techs.map(key));
  const pending = suggestions.filter(s => !used.has(key(s)));
  const update = (idx, patch) => onChange(techs.map((t, i) => (i === idx ? { ...t, ...patch } : t)));
  const onName = (idx, name) => {
    const hit = suggestions.find(s => s.name.toLowerCase() === name.trim().toLowerCase());
    update(idx, hit ? { name: hit.name, phone: hit.phone, email: hit.email, role: hit.role || techs[idx].role } : { name });
  };
  const addSuggested = (s) => onChange([...techs, { ...emptyTechnician(), name: s.name, phone: s.phone, email: s.email, role: s.role }]);

  return (
    <div className="rounded-lg border border-cyan-100 bg-cyan-50/30 p-3" data-testid={`${testPrefix}-reel`}>
      <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
        <p className="text-xs font-semibold text-cyan-900 flex items-center gap-1.5"><Wrench size={13} /> Reel de Contactos Técnicos Responsables
          <span className="font-normal text-cyan-700/70">({techs.length})</span></p>
        <Button type="button" size="sm" variant="outline" className="h-7 text-xs" onClick={() => onChange([...techs, emptyTechnician()])} data-testid={`${testPrefix}-add-btn`}>
          <Plus size={13} className="mr-1" /> Agregar Técnico Responsable
        </Button>
      </div>
      {pending.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 mb-2" data-testid={`${testPrefix}-suggestions`}>
          <span className="text-[11px] text-slate-500">Técnicos registrados del aplicativo:</span>
          {pending.slice(0, 8).map((s, i) => (
            <button key={i} type="button" onClick={() => addSuggested(s)} data-testid={`${testPrefix}-suggestion-${i}`}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] border border-cyan-300 bg-white text-cyan-800 hover:bg-cyan-600 hover:text-white transition-colors">
              <UserPlus size={11} />{s.name}{s.role ? ` · ${s.role}` : ''}
            </button>
          ))}
        </div>
      )}
      <datalist id={`${testPrefix}-names`}>{suggestions.map((s, i) => <option key={i} value={s.name} />)}</datalist>
      {techs.length === 0 && <p className="text-[11px] text-slate-400" data-testid={`${testPrefix}-empty`}>Sin técnicos asignados a esta integración.</p>}
      <div className="space-y-2">
        {techs.map((t, idx) => (
          <div key={idx} className="grid grid-cols-2 md:grid-cols-12 gap-2 bg-white border border-slate-200 rounded-md p-2" data-testid={`${testPrefix}-row-${idx}`}>
            <Input className="md:col-span-3 h-8 text-xs" placeholder="Nombre del Técnico *" list={`${testPrefix}-names`} value={t.name} onChange={e => onName(idx, e.target.value)} data-testid={`${testPrefix}-name-${idx}`} />
            <Input className="md:col-span-2 h-8 text-xs" placeholder="Teléfono" value={t.phone} onChange={e => update(idx, { phone: e.target.value })} data-testid={`${testPrefix}-phone-${idx}`} />
            <Input className="md:col-span-3 h-8 text-xs" placeholder="Correo electrónico" value={t.email} onChange={e => update(idx, { email: e.target.value })} data-testid={`${testPrefix}-email-${idx}`} />
            <ContactRoleSelect className="md:col-span-3 h-8" value={t.role} onChange={(v) => update(idx, { role: v })} testId={`${testPrefix}-role-${idx}`} />
            <Button type="button" size="sm" variant="ghost" className="md:col-span-1 h-8 w-8 p-0 text-red-500" onClick={() => onChange(techs.filter((_, i) => i !== idx))} data-testid={`${testPrefix}-remove-${idx}`}><X size={14} /></Button>
          </div>
        ))}
      </div>
    </div>
  );
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const technicianError = (techs) => {
  const bad = (techs || []).find(t => t.name.trim() && t.email && !EMAIL_RE.test(t.email.trim()));
  return bad ? `Correo inválido para el técnico ${bad.name}` : null;
};
