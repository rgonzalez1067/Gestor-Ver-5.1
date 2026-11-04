import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Mail, RefreshCw, Search, X, ChevronLeft, ChevronRight, Database } from 'lucide-react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import api from '../utils/api';

const STATUS = {
  sent: { label: 'Enviado', cls: 'bg-emerald-100 text-emerald-700' },
  error: { label: 'Fallido', cls: 'bg-rose-100 text-rose-700' },
  queued: { label: 'En Cola', cls: 'bg-sky-100 text-sky-700' },
  simulated: { label: 'Simulado', cls: 'bg-amber-100 text-amber-700' },
};
const EMPTY = { date_from: '', date_to: '', to: '', subject: '', status: 'all', action: 'all' };
const PAGE_SIZE = 25;

const fmt = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString('es-VE', { dateStyle: 'short', timeStyle: 'short' });
};
const fmtTo = (to) => (Array.isArray(to) ? to.join(', ') : String(to || '').replace(/[[\]']/g, ''));

const Field = ({ label, children }) => (
  <div><Label className="text-xs text-slate-500 mb-1 block">{label}</Label>{children}</div>
);

export default function EmailHistoryPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState(EMPTY);
  const [applied, setApplied] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ email_logs: [], total: 0, total_db: 0, pages: 1 });
  const [meta, setMeta] = useState({ actions: [], statuses: [] });
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, limit: PAGE_SIZE };
      Object.entries(applied).forEach(([k, v]) => { if (v && v !== 'all') params[k] = v; });
      const res = await api.get('/email-logs', { params });
      setData(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al cargar el historial de correos');
    } finally { setLoading(false); }
  }, [page, applied]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.get('/email-logs/actions').then(r => setMeta(r.data)).catch(() => {}); }, []);

  const apply = () => { setPage(1); setApplied(filters); };
  const clear = () => { setFilters(EMPTY); setPage(1); setApplied(EMPTY); };
  const set = (patch) => setFilters(f => ({ ...f, ...patch }));
  const filtered = Object.entries(applied).some(([, v]) => v && v !== 'all');

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 p-8" data-testid="email-history-page">
        <div className="max-w-7xl mx-auto">
          <Button variant="ghost" size="sm" onClick={() => navigate('/settings')} className="mb-4 -ml-3" data-testid="back-to-settings">
            <ArrowLeft size={16} className="mr-2" /> Volver a Configuración
          </Button>
          <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
            <div className="flex items-start gap-3">
              <div className="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0"><Mail size={26} /></div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900 font-manrope">Historial de Correos</h1>
                <p className="text-sm text-slate-600 mt-0.5">Auditoría de los correos despachados por el sistema.</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-white border border-slate-200 px-4 py-2 flex items-center gap-3" data-testid="email-history-total">
                <Database size={18} className="text-indigo-500" />
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Total registros en BD</p>
                  <p className="text-xl font-bold text-slate-900 tabular-nums" data-testid="email-history-total-db">{data.total_db.toLocaleString('es-VE')}</p>
                </div>
              </div>
              <Button variant="outline" onClick={load} disabled={loading} data-testid="email-history-refresh">
                <RefreshCw size={14} className={`mr-1.5 ${loading ? 'animate-spin' : ''}`} />Actualizar
              </Button>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4" data-testid="email-history-filters">
            <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-3">
              <Field label="Desde"><Input type="date" value={filters.date_from} onChange={e => set({ date_from: e.target.value })} data-testid="email-filter-date-from" /></Field>
              <Field label="Hasta"><Input type="date" value={filters.date_to} onChange={e => set({ date_to: e.target.value })} data-testid="email-filter-date-to" /></Field>
              <Field label="Destinatario"><Input placeholder="correo@..." value={filters.to} onChange={e => set({ to: e.target.value })} onKeyDown={e => e.key === 'Enter' && apply()} data-testid="email-filter-to" /></Field>
              <Field label="Asunto"><Input placeholder="Texto del asunto" value={filters.subject} onChange={e => set({ subject: e.target.value })} onKeyDown={e => e.key === 'Enter' && apply()} data-testid="email-filter-subject" /></Field>
              <Field label="Estatus de entrega">
                <Select value={filters.status} onValueChange={v => set({ status: v })}>
                  <SelectTrigger data-testid="email-filter-status"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    {Object.entries(STATUS).map(([k, s]) => <SelectItem key={k} value={k} data-testid={`email-filter-status-${k}`}>{s.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Tipo / Evento">
                <Select value={filters.action} onValueChange={v => set({ action: v })}>
                  <SelectTrigger data-testid="email-filter-action"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    {meta.actions.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
            </div>
            <div className="flex justify-end gap-2 mt-3">
              {filtered && <Button variant="ghost" size="sm" onClick={clear} data-testid="email-filter-clear"><X size={14} className="mr-1" />Limpiar</Button>}
              <Button size="sm" onClick={apply} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="email-filter-apply"><Search size={14} className="mr-1" />Buscar</Button>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-4 py-2.5 border-b text-xs text-slate-500 flex justify-between" data-testid="email-history-count">
              <span>{data.total.toLocaleString('es-VE')} registro(s){filtered ? ' con los filtros aplicados' : ''}</span>
              <span>Página {page} de {data.pages}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="email-history-table">
                <thead className="bg-slate-50 text-xs text-slate-500">
                  <tr>{['Estatus', 'Evento', 'Destinatario', 'Asunto', 'Cotización', 'Fecha'].map(h => <th key={h} className="px-4 py-2.5 text-left font-medium">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.email_logs.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-10 text-slate-400">{loading ? 'Cargando…' : 'No hay correos para estos filtros'}</td></tr>
                  ) : data.email_logs.map(l => {
                    const st = STATUS[l.status] || { label: l.status || '—', cls: 'bg-slate-100 text-slate-600' };
                    return (
                      <tr key={l.email_log_id} className="hover:bg-slate-50" data-testid={`email-history-row-${l.email_log_id}`}>
                        <td className="px-4 py-2.5"><span className={`px-2 py-0.5 text-xs font-medium rounded ${st.cls}`} title={l.error || ''}>{st.label}</span></td>
                        <td className="px-4 py-2.5 text-slate-600 text-xs">{l.action || '—'}</td>
                        <td className="px-4 py-2.5 text-slate-700 max-w-[240px] truncate" title={fmtTo(l.to)}>{fmtTo(l.to)}</td>
                        <td className="px-4 py-2.5 text-slate-700 max-w-[320px] truncate" title={l.subject}>{l.subject || '—'}</td>
                        <td className="px-4 py-2.5 text-slate-500 text-xs">{l.quote_number || '—'}</td>
                        <td className="px-4 py-2.5 text-slate-500 text-xs whitespace-nowrap">{fmt(l.created_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-end gap-2 px-4 py-2.5 border-t">
              <Button variant="outline" size="sm" disabled={page <= 1 || loading} onClick={() => setPage(p => p - 1)} data-testid="email-history-prev"><ChevronLeft size={14} /></Button>
              <span className="text-xs text-slate-500 tabular-nums">{page} / {data.pages}</span>
              <Button variant="outline" size="sm" disabled={page >= data.pages || loading} onClick={() => setPage(p => p + 1)} data-testid="email-history-next"><ChevronRight size={14} /></Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
