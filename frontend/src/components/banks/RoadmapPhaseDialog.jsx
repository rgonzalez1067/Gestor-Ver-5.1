import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { ArrowRight, ShieldCheck, UserCheck } from 'lucide-react';

export const RoadmapPhaseDialog = ({ open, onClose, change, implementers, currentUserId, onConfirm, saving }) => {
  const [ids, setIds] = useState([]);

  useEffect(() => {
    if (!open) return;
    const prev = (change?.intg?.equipo_fase || []).map(e => e.user_id);
    const fallback = implementers.some(u => u.user_id === currentUserId) ? [currentUserId] : [];
    setIds(prev.length ? prev : fallback);
  }, [open, change, implementers, currentUserId]);

  const toggle = (id) => setIds(p => (p.includes(id) ? p.filter(x => x !== id) : [...p, id]));

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md" data-testid="roadmap-phase-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <ShieldCheck size={20} className="text-orange-600" />Confirmar cambio de estatus
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <p className="text-sm font-semibold text-slate-800">{change?.intg?.service_name}</p>
            <p className="text-xs text-slate-500">{change?.intg?.component_type}</p>
            <div className="flex items-center gap-2 mt-2 text-sm font-semibold" data-testid="roadmap-phase-transition">
              <span className="px-2 py-0.5 rounded bg-white border border-slate-200">{change?.intg?.status}</span>
              <ArrowRight size={14} className="text-orange-600" />
              <span className="px-2 py-0.5 rounded bg-orange-600 text-white">{change?.to}</span>
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Recursos asignados a la fase {change?.to}</p>
            <p className="text-[11px] text-slate-400 mb-2">Coordinador u otros implementadores. Puede seleccionar varios.</p>
            <div className="max-h-[220px] overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100">
              {implementers.map(u => (
                <label key={u.user_id} className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-50 text-sm ${ids.includes(u.user_id) ? 'bg-orange-50' : ''}`}>
                  <input type="checkbox" checked={ids.includes(u.user_id)} onChange={() => toggle(u.user_id)}
                    className="h-4 w-4" data-testid={`roadmap-resource-${u.user_id}`} />
                  <span className="flex-1 truncate">{u.first_name} {u.last_name}</span>
                  <span className="text-[10px] text-slate-400">{u.cargo}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose} data-testid="roadmap-phase-cancel">Cancelar</Button>
            <Button onClick={() => onConfirm(ids)} disabled={!ids.length || saving}
              className="bg-orange-600 hover:bg-orange-700 text-white" data-testid="roadmap-phase-confirm">
              <UserCheck size={16} className="mr-1.5" />Confirmar y mover a {change?.to}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
