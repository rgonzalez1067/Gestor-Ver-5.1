import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { referenteLabel } from './ReferentePicker';
import { toast } from 'sonner';
import api from '../../utils/api';

export const MergeReferentesDialog = ({ open, selected, onClose, onMerged }) => {
  const [target, setTarget] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) setTarget(selected[0]?.referente_id || ''); }, [open, selected]);

  const merge = async () => {
    setSaving(true);
    try {
      const { data } = await api.post('/referentes/merge', { target_id: target, source_ids: selected.map((r) => r.referente_id).filter((id) => id !== target) });
      toast.success(`Fusionados ${data.referentes_fusionados} referente(s); ${data.contactos_reasignados} contacto(s) reasignado(s)`);
      onMerged(); onClose();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al fusionar'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid="merge-referentes-dialog">
        <DialogHeader>
          <DialogTitle>Fusionar Referentes duplicados</DialogTitle>
          <DialogDescription>Elija el referente que se conserva. Los Contactos Iniciales de los demás pasarán a él y los duplicados quedarán inactivos.</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          {selected.map((r) => (
            <label key={r.referente_id} className={`flex items-center gap-3 border rounded-md px-3 py-2 cursor-pointer ${target === r.referente_id ? 'border-brand-green-600 bg-green-50' : 'border-slate-200'}`}>
              <input type="radio" name="merge_target" checked={target === r.referente_id} onChange={() => setTarget(r.referente_id)} data-testid={`merge-target-${r.referente_id}`} />
              <span className="text-sm flex-1">{referenteLabel(r)}</span>
              <span className="text-xs text-slate-500">{r.contactos} contacto(s)</span>
            </label>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="merge-cancel-btn">Cancelar</Button>
          <Button onClick={merge} disabled={saving || !target} className="bg-brand-green-600 hover:bg-brand-green-700" data-testid="merge-confirm-btn">{saving ? 'Fusionando...' : 'Fusionar'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
