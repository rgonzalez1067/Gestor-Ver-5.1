import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { CalendarClock, Download, Loader2, PlayCircle, RefreshCw } from 'lucide-react';
import api from '../../utils/api';
import { Button } from '../ui/button';

const mb = (b) => `${((b || 0) / (1024 * 1024)).toFixed(1)} MB`;
const STATUS = { ok: ['Listo', 'text-emerald-700 bg-emerald-50 border-emerald-200'], error: ['Con errores', 'text-red-700 bg-red-50 border-red-200'], running: ['En curso', 'text-amber-700 bg-amber-50 border-amber-200'] };

export const ScheduledBackupsCard = () => {
  const [data, setData] = useState(null);
  const [starting, setStarting] = useState(false);

  const load = useCallback(() => api.get('/admin/scheduled-backups').then(r => setData(r.data)).catch(() => setData({ runs: [] })), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!data?.runs?.some(r => r.status === 'running')) return undefined;
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [data, load]);

  const runNow = async () => {
    if (!window.confirm('¿Generar ahora el respaldo completo (BD + Maestras + Archivos)? Puede tardar varios minutos.')) return;
    setStarting(true);
    try { await api.post('/admin/scheduled-backups/run-now'); toast.success('Respaldo iniciado. Se avisará por correo al terminar.'); setTimeout(load, 1500); }
    catch (e) { toast.error(e.response?.data?.detail || 'No se pudo iniciar'); }
    finally { setStarting(false); }
  };

  const download = async (jobId) => {
    try {
      const { data: tk } = await api.post('/admin/full-backup/export-ticket', { job_id: jobId });
      const a = document.createElement('a');
      a.href = `${process.env.REACT_APP_BACKEND_URL}/api/admin/full-backup/export?ticket=${encodeURIComponent(tk.ticket)}`;
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al descargar'); }
  };

  const runs = data?.runs || [];
  return (
    <div className="bg-white rounded-xl border border-indigo-200 shadow-sm mb-6 p-5" data-testid="scheduled-backups-card">
      <div className="flex items-start gap-3">
        <CalendarClock size={22} className="text-indigo-600 mt-0.5" />
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-slate-900">Respaldos Programados</h2>
          <p className="text-xs text-slate-500 mt-0.5" data-testid="scheduled-backups-schedule">
            Automático: {data?.schedule || 'Lunes, Miércoles y Viernes 8:00 PM'}. Incluye Base de Datos, Maestras y Archivos.
            Se conservan las últimas {data?.keep_runs || 2} ejecuciones y se avisa por correo a los administradores.
          </p>
        </div>
        <Button size="sm" variant="ghost" onClick={load} data-testid="scheduled-backups-refresh"><RefreshCw size={14} /></Button>
        <Button size="sm" onClick={runNow} disabled={starting || runs.some(r => r.status === 'running')} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="scheduled-backups-run-now">
          {starting ? <Loader2 size={14} className="mr-1 animate-spin" /> : <PlayCircle size={14} className="mr-1" />}Generar ahora
        </Button>
      </div>
      <div className="mt-4 space-y-3">
        {data && runs.length === 0 && <p className="text-xs text-slate-400" data-testid="scheduled-backups-empty">Aún no hay respaldos programados generados.</p>}
        {runs.map(r => {
          const [lbl, cls] = STATUS[r.status] || STATUS.running;
          return (
            <div key={r.run_id} className="border border-slate-200 rounded-lg p-3" data-testid={`scheduled-run-${r.run_id}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-semibold text-slate-800">{r.fecha_local}</span>
                <span className={`text-[11px] px-2 py-0.5 rounded border ${cls}`}>{lbl}</span>
              </div>
              {(r.parts || []).map(p => (
                <div key={p.job_id} className="flex items-center justify-between text-xs py-1 border-t border-slate-100">
                  <span className="text-slate-600">{p.label}</span>
                  {p.status === 'ready'
                    ? <Button size="sm" variant="outline" className="h-7" onClick={() => download(p.job_id)} data-testid={`scheduled-download-${p.job_id}`}>
                        <Download size={12} className="mr-1" />{mb(p.size_bytes)}
                      </Button>
                    : <span className="text-red-600" title={p.error || ''}>Error</span>}
                </div>
              ))}
              {r.status === 'running' && <p className="text-[11px] text-amber-700 mt-1 flex items-center gap-1"><Loader2 size={11} className="animate-spin" />Generando ({(r.parts || []).length}/3 paquetes)...</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
};
