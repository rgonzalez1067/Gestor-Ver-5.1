import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Trash2, RotateCcw, Archive, AlertTriangle } from 'lucide-react';

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString('es-VE', { dateStyle: 'short', timeStyle: 'short' }) : '—');

// Modal de eliminación con motivo obligatorio (el proyecto va a la Papelera).
export const DeleteProjectDialog = ({ project, onClose, onDeleted }) => {
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { setReason(''); }, [project]);
  const ok = reason.trim().length >= 10;
  const submit = async () => {
    setBusy(true);
    try {
      await api.delete(`/projects/${project.project_id}`, { params: { reason: reason.trim() } });
      toast.success('Proyecto enviado a la papelera');
      onClose();
      onDeleted?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al eliminar');
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={!!project} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid="delete-project-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2 text-red-700"><Trash2 size={18} /> Eliminar Proyecto</DialogTitle></DialogHeader>
        <p className="text-sm text-slate-600">
          <b>{project?.project_number}</b> · {project?.client_name}. El proyecto irá a la <b>Papelera</b>, desde donde un administrador podrá restaurarlo.
        </p>
        <div>
          <label className="text-sm font-semibold text-slate-800">Motivo de la eliminación <span className="text-red-500">*</span></label>
          <textarea rows={3} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} data-testid="delete-project-reason"
            placeholder="Explica por qué se elimina este proyecto" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
          <p className={`text-[11px] ${ok ? 'text-slate-400' : 'text-red-500'}`}>{ok ? `${reason.trim().length}/1000` : 'Obligatorio · mínimo 10 caracteres'}</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="delete-project-cancel">Cancelar</Button>
          <Button onClick={submit} disabled={!ok || busy} className="bg-red-600 hover:bg-red-700" data-testid="delete-project-confirm">{busy ? 'Eliminando…' : 'Enviar a Papelera'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const TrashRow = ({ t, onRestore, onPurge }) => (
  <tr className="hover:bg-slate-50" data-testid={`trash-row-${t.project_id}`}>
    <td className="px-3 py-2 font-medium">{t.project_number}<p className="text-[11px] text-slate-400">{t.ticket_number || 'Sin ticket'} · {t.status}</p></td>
    <td className="px-3 py-2">{t.client_name}</td>
    <td className="px-3 py-2 text-xs">{fmtDate(t.deleted_at)}<p className="text-slate-500">{t.deleted_by_name}</p></td>
    <td className="px-3 py-2 text-xs text-slate-600 max-w-[260px]">{t.reason}</td>
    <td className="px-3 py-2 text-right whitespace-nowrap">
      <Button size="sm" variant="outline" onClick={() => onRestore(t)} className="h-7 text-emerald-700 border-emerald-300" data-testid={`trash-restore-${t.project_id}`}><RotateCcw size={13} className="mr-1" />Restaurar</Button>
      <Button size="sm" variant="outline" onClick={() => onPurge(t)} className="h-7 ml-1 text-red-600 border-red-200" title="Eliminar definitivamente" data-testid={`trash-purge-${t.project_id}`}><Trash2 size={13} /></Button>
    </td>
  </tr>
);

// Papelera de Proyectos (solo administradores).
export const ProjectsTrashDialog = ({ open, onOpenChange, onRestored }) => {
  const [items, setItems] = useState([]);
  const load = () => api.get('/projects-trash').then(r => setItems(r.data)).catch(() => toast.error('No se pudo cargar la papelera'));
  useEffect(() => { if (open) load(); }, [open]);
  const restore = async (t) => {
    try {
      await api.post(`/projects-trash/${t.project_id}/restore`);
      toast.success(`Proyecto ${t.project_number} restaurado`);
      load();
      onRestored?.();
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo restaurar'); }
  };
  const purge = async (t) => {
    if (!window.confirm(`¿Eliminar DEFINITIVAMENTE ${t.project_number}? No podrá recuperarse.`)) return;
    try { await api.delete(`/projects-trash/${t.project_id}`); toast.success('Eliminado definitivamente'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
  };
  const empty = async () => {
    if (!window.confirm(`¿Vaciar la papelera? Se eliminarán definitivamente ${items.length} proyecto(s).`)) return;
    try { await api.delete('/projects-trash'); toast.success('Papelera vaciada'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl" data-testid="projects-trash-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Archive size={18} className="text-slate-600" /> Papelera de Proyectos <span className="text-sm font-normal text-slate-500">({items.length})</span></DialogTitle></DialogHeader>
        <div className="border rounded-lg max-h-[60vh] overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-600 sticky top-0">
              <tr><th className="px-3 py-2 text-left">Proyecto</th><th className="px-3 py-2 text-left">Cliente</th><th className="px-3 py-2 text-left">Eliminado</th><th className="px-3 py-2 text-left">Motivo</th><th /></tr>
            </thead>
            <tbody className="divide-y">
              {items.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-400" data-testid="trash-empty">La papelera está vacía.</td></tr>}
              {items.map(t => <TrashRow key={t.project_id} t={t} onRestore={restore} onPurge={purge} />)}
            </tbody>
          </table>
        </div>
        <DialogFooter className="sm:justify-between">
          <p className="text-xs text-slate-500 flex items-center gap-1"><AlertTriangle size={12} /> Los proyectos permanecen aquí hasta que un administrador los restaure o vacíe la papelera.</p>
          <Button variant="outline" disabled={!items.length} onClick={empty} className="text-red-600 border-red-200" data-testid="trash-empty-btn"><Trash2 size={14} className="mr-1" />Vaciar papelera</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
