import { useEffect, useMemo, useState } from 'react';
import { Button } from '../../ui/button';
import { Pencil, Lock } from 'lucide-react';
import { ReasonField, reasonError } from './ReasonField';
import { buildPayload, CERT_STATES, CERT_CYCLE } from './appPayload';
import { toggleRequest } from './ProductRequestPicker';
import api from '../../../utils/api';
import { toast } from 'sonner';

export const AppMatrixTab = ({ app, products, editable, locked, onSaved }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({});
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => { setEditing(false); setReason(''); }, [app]);

  const certs = editing ? draft : (app.certifications || {});
  const counts = useMemo(() => {
    const c = { C: 0, P: 0, 'N/A': 0, S: 0, R: 0 };
    products.forEach((p) => { c[certs[p.service_id] || 'N/A'] += 1; });
    return c;
  }, [products, certs]);
  const changed = editing && products.filter((p) => (draft[p.service_id] || 'N/A') !== ((app.certifications || {})[p.service_id] || 'N/A')).length;

  const isProject = app.project_scope === 'expansion';
  const cycle = (pid) => setDraft((d) => {
    const cur = d[pid] || 'N/A';
    if (isProject) return { ...d, [pid]: toggleRequest(cur, (app.certifications || {})[pid] || 'N/A') };
    return { ...d, [pid]: CERT_CYCLE[(CERT_CYCLE.indexOf(cur) + 1) % CERT_CYCLE.length] };
  });
  const save = async () => {
    const err = reasonError(locked, reason);
    if (err) { toast.error(err); return; }
    setSaving(true);
    try {
      await api.put(`/integrators/${app.integrator_id}`, buildPayload(app, { certifications: draft, change_reason: reason.trim() || null }));
      toast.success('Matriz de Productos actualizada'); setEditing(false); onSaved();
    } catch (e) { toast.error(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Error al guardar la matriz'); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-3" data-testid="app-matrix-tab">
      <div className="flex items-center gap-2 flex-wrap">
        {Object.entries(CERT_STATES).map(([k, s]) => (
          <span key={k} className={`px-2.5 py-1 rounded-full border text-[11px] font-semibold ${s.color}`} data-testid={`matrix-count-${k}`}>{k} {s.text} · {counts[k]}</span>
        ))}
        <div className="flex-1" />
        {!editable && locked && <span className="text-[11px] text-slate-500 inline-flex items-center gap-1" data-testid="matrix-locked-note"><Lock size={12} />Solo lectura — requiere Función Especial</span>}
        {editable && !editing && <Button size="sm" variant="outline" onClick={() => { setDraft({ ...(app.certifications || {}) }); setReason(''); setEditing(true); }} data-testid="matrix-edit-btn"><Pencil size={13} className="mr-1" />Modificar matriz</Button>}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
        {products.map((p) => {
          const val = certs[p.service_id] || 'N/A';
          const st = CERT_STATES[val] || CERT_STATES['N/A'];
          const dirty = editing && val !== ((app.certifications || {})[p.service_id] || 'N/A');
          return (
            <div key={p.service_id} className={`flex items-center justify-between gap-2 rounded-md border px-3 py-2 bg-white transition-colors ${dirty ? 'border-amber-400 ring-1 ring-amber-200' : 'border-slate-200'}`}>
              <span className="text-xs text-slate-700 leading-tight">{p.name}
                {(app.cert_baseline || []).includes(p.service_id) && val === 'C' && <span className="block text-[10px] text-emerald-600" data-testid={`matrix-certified-${p.service_id}`}>Ya certificado</span>}
              </span>
              <button type="button" disabled={!editing} onClick={() => cycle(p.service_id)} data-testid={`matrix-cell-${p.service_id}`}
                className={`min-w-[44px] px-2 py-1 rounded border text-xs font-bold transition-transform ${st.color} ${editing ? 'cursor-pointer hover:scale-105' : 'cursor-default'}`}>{st.label}</button>
            </div>
          );
        })}
      </div>
      {editing && (
        <div className="space-y-3 border-t pt-3">
          <p className="text-xs text-slate-500" data-testid="matrix-changed-count">{changed} producto(s) modificado(s). {isProject ? 'Pulse un producto disponible para marcarlo S (Solicitado) o uno certificado (C) para R (Recertificación); pulse de nuevo para revertir.' : 'Haz clic en cada estado para alternar P → C → N/A.'}</p>
          {locked && <ReasonField value={reason} onChange={setReason} testId="matrix-reason" />}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setEditing(false)} data-testid="matrix-cancel-btn">Cancelar</Button>
            <Button size="sm" disabled={saving || !changed} onClick={save} className="bg-brand-green-600 hover:bg-brand-green-700" data-testid="matrix-save-btn">{saving ? 'Guardando...' : 'Guardar matriz'}</Button>
          </div>
        </div>
      )}
    </div>
  );
};
