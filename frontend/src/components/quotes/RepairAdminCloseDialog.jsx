import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShieldAlert, Loader2, Paperclip, X } from 'lucide-react';
import api from '../../utils/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

const ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp,.eml';

// Cierre Administrativo (todas las cotizaciones): archiva en el Histórico con motivo obligatorio.
export const RepairAdminCloseDialog = ({ quoteId, onClose, onDone }) => {
  const [check, setCheck] = useState(null);
  const [reason, setReason] = useState('');
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!quoteId) return;
    setCheck(null); setReason(''); setFile(null);
    api.get(`/quotes/${quoteId}/admin-close/check`).then(r => setCheck(r.data))
      .catch(e => setCheck({ eligible: false, reason: e.response?.data?.detail || 'No se pudo validar la cotización' }));
  }, [quoteId]);

  const pickFile = (f) => {
    if (!f) return;
    if (f.size > 10 * 1024 * 1024) { toast.error('El soporte supera 10 MB'); return; }
    setFile(f);
  };
  const submit = async () => {
    setSaving(true);
    try {
      const fd = new FormData();
      fd.append('reason', reason.trim());
      if (file) fd.append('file', file);
      await api.post(`/quotes/${quoteId}/admin-close`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success(`${check?.quote_number} cerrada administrativamente y enviada al Histórico`);
      onDone?.(); onClose();
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo cerrar la cotización'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={!!quoteId} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg" data-testid="admin-close-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><ShieldAlert size={18} className="text-amber-600" />Cierre Administrativo {check?.quote_number ? `· ${check.quote_number}` : ''}</DialogTitle>
        </DialogHeader>
        {!check ? <div className="py-6 text-center"><Loader2 className="mx-auto animate-spin text-slate-400" /></div> : !check.eligible ? (
          <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700" data-testid="admin-close-ineligible">{check.reason}</p>
        ) : (
          <div className="space-y-4">
            <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              La cotización <b>{check.quote_number}</b>{check.client_name ? ` (${check.client_name})` : ''} en estatus <b>{check.quote_status}</b> saldrá
              de Cotizaciones y pasará al <b>Histórico</b> con marca de <b>Cierre Administrativo</b>. No se mueven equipos ni inventario.
              Si la acción tiene notificaciones configuradas, se enviarán.
            </p>
            <div>
              <label className="text-xs font-medium text-slate-600">Motivo del cierre (obligatorio)</label>
              <Textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} placeholder="Ej.: Cliente desistió del servicio; se cierra para depurar la cartera."
                data-testid="admin-close-reason" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600">Documento de soporte (opcional · PDF, imagen o .eml, máx. 10 MB)</label>
              {file ? (
                <div className="mt-1 flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm" data-testid="admin-close-file">
                  <Paperclip size={14} className="text-slate-500" /><span className="flex-1 truncate">{file.name}</span>
                  <button type="button" onClick={() => setFile(null)} className="text-slate-400 hover:text-red-600" data-testid="admin-close-file-remove"><X size={14} /></button>
                </div>
              ) : (
                <input type="file" accept={ACCEPT} onChange={e => pickFile(e.target.files?.[0])} className="mt-1 block w-full text-sm" data-testid="admin-close-file-input" />
              )}
              <p className="mt-1 text-[11px] text-slate-400">También podrá cargarla después desde Anexos en el Histórico de Cotizaciones.</p>
            </div>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="admin-close-cancel">Cancelar</Button>
          {check?.eligible && (
            <Button onClick={submit} disabled={saving || reason.trim().length < 10} className="bg-amber-600 hover:bg-amber-700 text-white" data-testid="admin-close-confirm">
              {saving && <Loader2 size={14} className="mr-1 animate-spin" />}Confirmar Cierre Administrativo
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
