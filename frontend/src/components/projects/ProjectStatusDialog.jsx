import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Clock, UserCheck, UserCog, Pause, Snowflake, CheckCircle2, X, AlertTriangle, Ticket, Paperclip, RefreshCw } from 'lucide-react';

export const STATUS_CONFIG = {
  'Por asignar': { color: 'bg-amber-100 text-amber-800 border-amber-200', icon: Clock },
  'Asignado': { color: 'bg-blue-100 text-blue-800 border-blue-200', icon: UserCheck },
  'En Gestión': { color: 'bg-indigo-100 text-indigo-800 border-indigo-200', icon: UserCog },
  'Configurado en espera del Cliente': { color: 'bg-cyan-100 text-cyan-800 border-cyan-200', icon: Pause },
  'Congelado': { color: 'bg-blue-100 text-blue-800 border-blue-200', icon: Snowflake },
  'Suspendido': { color: 'bg-red-100 text-red-800 border-red-200', icon: Pause },
  'Implementado parcial': { color: 'bg-orange-100 text-orange-800 border-orange-200', icon: CheckCircle2 },
  'Culminado': { color: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: CheckCircle2 },
  'Anulado': { color: 'bg-slate-200 text-slate-700 border-slate-300', icon: X },
};

// Estados que se ocultan por defecto en la bandeja (cerrados / pausados).
export const HIDDEN_DEFAULT_STATES = ['Suspendido', 'Implementado parcial', 'Culminado', 'Anulado'];
// Estados que disparan recordatorio de cierre de ticket en el portal
// (proyecto cerrado / suspendido / anulado).
export const TICKET_REMINDER_STATES = ['Culminado', 'Suspendido', 'Anulado'];

// Toast ROJO prominente (esquina superior derecha) para recordar el cierre del
// Ticket cuando un proyecto pasa a un estado terminal/pausado.
export const showTicketReminderToast = (status) => {
  toast.custom((t) => (
    <div
      className="w-[380px] bg-red-600 text-white rounded-xl shadow-2xl ring-2 ring-red-300/70 overflow-hidden"
      data-testid="ticket-reminder-toast"
      data-status={status}
    >
      <div className="flex items-start gap-3 p-4">
        <div className="shrink-0 mt-0.5 bg-white/20 rounded-lg p-2">
          <AlertTriangle size={22} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-bold text-sm leading-snug flex items-center gap-1.5">
            <Ticket size={15} /> Recuerde cerrar el Ticket
          </p>
          <p className="text-xs text-white/90 mt-1 break-words">
            El proyecto pasó a <strong>{status}</strong>. Cierre el Ticket en el portal al confirmar este estado.
          </p>
        </div>
        <button
          onClick={() => toast.dismiss(t)}
          className="shrink-0 p-1 rounded-lg hover:bg-white/15 transition-colors"
          aria-label="Cerrar"
          data-testid="ticket-reminder-close-btn"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  ), { duration: 10000 });
};

// Estados asignables MANUALMENTE por el usuario vía "Cambiar estado".
// Los estados automáticos (Por asignar, Asignado, En Gestión) responden a triggers.
const STATUS_TRANSITIONS = [
  { id: 'En Gestión', label: 'En Gestión (Reactivar)', icon: UserCog, iconColor: 'text-indigo-600', reactivation: true },
  { id: 'Congelado', label: 'Congelar Proyecto', icon: Snowflake, iconColor: 'text-blue-600', freezeOnly: true },
  { id: 'Configurado en espera del Cliente', label: 'Configurado en espera del Cliente', icon: Pause, iconColor: 'text-cyan-600' },
  { id: 'Suspendido', label: 'Suspendido', icon: Pause, iconColor: 'text-red-600' },
  { id: 'Implementado parcial', label: 'Implementado parcial', icon: CheckCircle2, iconColor: 'text-orange-600' },
  { id: 'Culminado', label: 'Culminado', icon: CheckCircle2, iconColor: 'text-emerald-600' },
  { id: 'Anulado', label: 'Anulado', icon: X, iconColor: 'text-slate-600' },
];

// Cuerpo del modal de cambio de estado con ESTADO LOCAL propio: al escribir la
// justificación NO se re-renderiza la grilla completa (evita el lag por carácter).
export function StatusDialogBody({ project, loading, onCancel, onConfirm }) {
  const [form, setForm] = useState({ new_status: '', note: '', change_date: new Date().toISOString().slice(0, 10) });
  const [file, setFile] = useState(null);

  useEffect(() => {
    setForm({ new_status: '', note: '', change_date: new Date().toISOString().slice(0, 10) });
    setFile(null);
  }, [project?.project_id]);

  return (
    <div className="space-y-4">
      <div className="bg-slate-50 border rounded-lg p-3">
        <p className="font-semibold text-sm">{project.project_number}</p>
        <p className="text-xs text-slate-500">{project.client_name}</p>
        <div className="mt-2">
          <span className="text-[10px] text-slate-500 uppercase">Estado actual:</span>
          <span className={`ml-2 inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${STATUS_CONFIG[project.status]?.color || ''}`}>
            {project.status}
          </span>
        </div>
      </div>

      {/* Status options */}
      <div>
        <Label className="text-sm">Nuevo Estado</Label>
        <div className="space-y-1.5 mt-1.5">
          {STATUS_TRANSITIONS.filter(t => {
            if (t.id === project.status) return false;
            if (t.freezeOnly) return project.status === 'En Gestión';
            if (t.reactivation) return HIDDEN_DEFAULT_STATES.includes(project.status) || project.status === 'Congelado';
            if (project.status === 'Congelado') return false;
            return true;
          }).map(t => {
            const TIcon = t.icon;
            const selected = form.new_status === t.id;
            const dynLabel = (t.reactivation && project.status === 'Congelado')
              ? 'Descongelar (volver a En Gestión)' : t.label;
            return (
              <button key={t.id} onClick={() => setForm(p => ({ ...p, new_status: t.id }))}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 text-left transition-all ${selected ? 'border-slate-800 bg-slate-50 shadow-sm' : 'border-slate-200 hover:border-slate-300'}`}
                data-testid={`status-option-${t.id.replace(/[\s\/]/g, '-').toLowerCase()}`}>
                <TIcon size={18} className={t.iconColor} />
                <span className="text-sm font-medium text-slate-800">{dynLabel}</span>
                {selected && <CheckCircle2 size={16} className="ml-auto text-slate-800" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* Date + Comment (justificación obligatoria) */}
      {form.new_status && (
        <div className="space-y-3 pt-2 border-t border-slate-200 animate-in fade-in-0 slide-in-from-top-1">
          {TICKET_REMINDER_STATES.includes(form.new_status) && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-2.5 text-amber-800" data-testid="status-ticket-reminder">
              <AlertTriangle size={15} className="mt-0.5 shrink-0" />
              <span className="text-xs">Recuerde <strong>cerrar el Ticket</strong> en el portal al confirmar este estado.</span>
            </div>
          )}
          <div>
            <Label className="text-sm">Fecha del Cambio</Label>
            <Input type="date" value={form.change_date}
              onChange={e => setForm(p => ({ ...p, change_date: e.target.value }))}
              className="mt-1" data-testid="status-change-date" />
          </div>
          <div>
            <Label className="text-sm">Comentario de Justificación <span className="text-red-500">*</span></Label>
            <Textarea value={form.note}
              onChange={e => setForm(p => ({ ...p, note: e.target.value }))}
              placeholder="Motivo o detalle del cambio de estado (obligatorio)..."
              className="mt-1 min-h-[60px] text-sm" data-testid="status-change-comment" />
          </div>
          <div>
            <Label className="text-sm">Anexo (opcional)</Label>
            <Input type="file" onChange={e => setFile(e.target.files?.[0] || null)}
              className="mt-1 text-sm" data-testid="status-change-file" />
            {file && (
              <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                <Paperclip size={11} />{file.name}
              </p>
            )}
          </div>
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2 border-t">
        <Button variant="outline" onClick={onCancel}>Cancelar</Button>
        <Button onClick={() => onConfirm(form, file)}
          disabled={loading || !form.new_status || !form.note.trim()}
          className="bg-orange-600 hover:bg-orange-700 text-white"
          data-testid="status-change-confirm-btn">
          {loading ? 'Actualizando...' : 'Confirmar Cambio'}
        </Button>
      </div>
    </div>
  );
}

// Diálogo "Cambiar Estado" compartido por la grilla de Proyectos y la ficha del proyecto.
export const ProjectStatusDialog = ({ project, open, onOpenChange, onChanged }) => {
  const [loading, setLoading] = useState(false);
  const handleConfirm = async (form, file) => {
    if (!form.new_status) { toast.error('Seleccione un estado'); return; }
    if (!form.note.trim()) { toast.error('El comentario de justificación es obligatorio'); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('new_status', form.new_status);
      fd.append('note', form.note);
      fd.append('change_date', form.change_date || '');
      if (file) fd.append('file', file);
      await api.put(`/projects/${project.project_id}/status`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success(`Estado: ${form.new_status}`);
      if (TICKET_REMINDER_STATES.includes(form.new_status)) showTicketReminderToast(form.new_status);
      onOpenChange(false);
      onChanged?.(form.new_status);
    } catch (err) { toast.error(err.response?.data?.detail || 'Error al cambiar estado'); }
    finally { setLoading(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="status-change-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw size={20} className="text-orange-500" />
            Cambiar Estado del Proyecto
          </DialogTitle>
        </DialogHeader>
        {project && <StatusDialogBody project={project} loading={loading} onCancel={() => onOpenChange(false)} onConfirm={handleConfirm} />}
      </DialogContent>
    </Dialog>
  );
};
