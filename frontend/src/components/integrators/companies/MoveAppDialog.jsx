import { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import api from '../../../utils/api';
import { toast } from 'sonner';

export const MoveAppDialog = ({ app, companies, onClose, onMoved }) => {
  const [q, setQ] = useState('');
  const [target, setTarget] = useState('');
  const options = useMemo(() => {
    const s = q.trim().toLowerCase();
    return companies.filter(c => c.empresa_id !== app?.empresa_integradora_id && (!s || c.razon_social.toLowerCase().includes(s) || (c.rif || '').toLowerCase().includes(s))).slice(0, 60);
  }, [companies, q, app]);

  const move = async () => {
    try {
      const { data } = await api.put(`/integrators/${app.integrator_id}/company`, { empresa_integradora_id: target });
      toast.success(data.message); onClose(); onMoved();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al mover el aplicativo'); }
  };

  return (
    <Dialog open={!!app} onOpenChange={(o) => { if (!o) { onClose(); setQ(''); setTarget(''); } }}>
      <DialogContent className="max-w-lg" data-testid="move-app-dialog">
        <DialogHeader><DialogTitle className="text-base">Mover «{app?.app_name}» a otra Empresa Integradora</DialogTitle></DialogHeader>
        <Input placeholder="Buscar empresa por nombre o RIF..." value={q} onChange={e => setQ(e.target.value)} data-testid="move-app-search" />
        <div className="max-h-72 overflow-y-auto border rounded-md divide-y">
          {options.map(c => (
            <button key={c.empresa_id} type="button" onClick={() => setTarget(c.empresa_id)} data-testid={`move-app-option-${c.empresa_id}`}
              className={`w-full text-left px-3 py-2 text-sm transition-colors ${target === c.empresa_id ? 'bg-brand-blue-50 text-brand-blue-700 font-semibold' : 'hover:bg-slate-50'}`}>
              {c.razon_social} <span className="text-xs text-slate-400 ml-1">{c.rif || 'Sin RIF'} · {c.app_count} app(s)</span>
            </button>
          ))}
          {!options.length && <p className="px-3 py-3 text-xs text-slate-400">Sin coincidencias</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button disabled={!target} onClick={move} data-testid="move-app-confirm-btn">Mover aplicativo</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
