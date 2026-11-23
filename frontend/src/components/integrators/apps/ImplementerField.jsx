import { useState } from 'react';
import { Button } from '../../ui/button';
import { Label } from '../../ui/label';
import { Pencil, Check, X } from 'lucide-react';
import api from '../../../utils/api';
import { toast } from 'sonner';

export const ImplementerField = ({ app, isAdmin, onSaved }) => {
  const [editing, setEditing] = useState(false);
  const [users, setUsers] = useState([]);
  const [target, setTarget] = useState('');
  const [saving, setSaving] = useState(false);

  const start = async () => {
    setTarget(app.implementador_user_id || '');
    setEditing(true);
    try { setUsers((await api.get('/auth/implementadores')).data || []); }
    catch { toast.error('No se pudo cargar la lista de implementadores'); }
  };
  const save = async () => {
    if (!target || target === app.implementador_user_id) { setEditing(false); return; }
    setSaving(true);
    try {
      const { data } = await api.put(`/integrators/${app.integrator_id}/assign-implementador`, { user_id: target });
      toast.success(data?.message || 'Implementador actualizado');
      setEditing(false); onSaved();
    } catch (e) { toast.error(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Error al cambiar el implementador'); }
    finally { setSaving(false); }
  };

  return (
    <div data-testid="app-implementer-field">
      <Label className="text-[11px] uppercase tracking-wide text-slate-400">Implementador</Label>
      {editing ? (
        <div className="flex items-center gap-1">
          <select className="h-8 flex-1 min-w-0 rounded-md border border-input bg-white px-2 text-sm" value={target} onChange={(e) => setTarget(e.target.value)} data-testid="app-implementer-select">
            <option value="">— Seleccione —</option>
            {users.map((u) => <option key={u.user_id} value={u.user_id}>{u.full_name || u.email}</option>)}
          </select>
          <Button size="sm" className="h-8 w-8 p-0 bg-brand-green-600 hover:bg-brand-green-700" disabled={saving || !target} onClick={save} data-testid="app-implementer-save-btn"><Check size={14} /></Button>
          <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => setEditing(false)} data-testid="app-implementer-cancel-btn"><X size={14} /></Button>
        </div>
      ) : (
        <div className="flex items-center gap-1.5">
          <p className="text-sm text-slate-600" data-testid="app-value-implementador">{app.implementador || '—'}</p>
          {isAdmin && <button type="button" onClick={start} className="text-slate-400 hover:text-brand-blue-600" title="Cambiar implementador (solo Administrador)" data-testid="app-implementer-edit-btn"><Pencil size={12} /></button>}
        </div>
      )}
    </div>
  );
};
