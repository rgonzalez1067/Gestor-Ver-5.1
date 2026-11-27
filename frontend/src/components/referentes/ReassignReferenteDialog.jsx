import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Shuffle } from 'lucide-react';
import api from '../../utils/api';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { ReferentePicker } from './ReferentePicker';

// Solo Admin: reasigna el Referente de un Contacto Inicial para consolidar nombres similares.
export const ReassignReferenteDialog = ({ contact, referentes, onClose, onDone }) => {
  const [value, setValue] = useState({ referente_id: '', nuevo: null });
  const [comment, setComment] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => { setValue({ referente_id: '', nuevo: null }); setComment(''); }, [contact]);

  const submit = async () => {
    setSaving(true);
    try {
      await api.put(`/initial-contacts/${contact.contact_id}/referente`, { referente_id: value.referente_id, comment });
      toast.success('Referente reasignado');
      onDone?.(); onClose();
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo reasignar el referente'); }
    finally { setSaving(false); }
  };

  const options = (referentes || []).filter(r => r.estatus !== false && r.referente_id !== contact?.referente_id);
  return (
    <Dialog open={!!contact} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md" data-testid="reassign-referente-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Shuffle size={18} className="text-violet-600" />Reasignar Referente</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
            <p className="font-semibold text-slate-800">{contact?.legal_name || contact?.contact_name}</p>
            <p className="text-xs text-slate-500 mt-1">Referente actual: <b data-testid="reassign-current-referente">{contact?.referred_by || '—'}</b></p>
          </div>
          <div>
            <Label className="text-xs">Nuevo referente (consolidado) *</Label>
            <ReferentePicker referentes={options} canCreate={false} value={value} onChange={setValue} testId="reassign-referente-picker" />
          </div>
          <div>
            <Label className="text-xs">Comentario (opcional)</Label>
            <Textarea rows={2} value={comment} onChange={e => setComment(e.target.value)} placeholder="Ej.: Consolidación de nombres duplicados" data-testid="reassign-referente-comment" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="reassign-referente-cancel">Cancelar</Button>
          <Button onClick={submit} disabled={!value.referente_id || saving} className="bg-violet-600 hover:bg-violet-700 text-white" data-testid="reassign-referente-confirm">
            {saving && <Loader2 size={14} className="mr-1 animate-spin" />}Reasignar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
