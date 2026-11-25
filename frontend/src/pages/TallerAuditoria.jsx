import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShieldCheck, Search, Download, CheckCircle2, AlertOctagon, ClipboardList, AlertTriangle } from 'lucide-react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import api from '../utils/api';

const ESTATUS = ['Recibido', 'Cotizado', 'En reparación', 'Reparado', 'Pagado', 'Entregado'];
const NIVEL_STYLE = {
  INCONSISTENCIA: { row: 'bg-rose-50/70', dot: 'bg-rose-500', text: 'text-rose-700' },
  ALERTA: { row: 'bg-amber-50/70', dot: 'bg-amber-500', text: 'text-amber-700' },
  OK: { row: '', dot: 'bg-emerald-500', text: 'text-emerald-700' },
};
const fmt = (d) => (d ? d.slice(0, 10).split('-').reverse().join('/') : '—');

const Kpi = ({ icon: Icon, label, value, tone, testid }) => (
  <div className={`rounded-xl border bg-white px-4 py-3 flex items-center gap-3 ${tone}`} data-testid={testid}>
    <Icon size={20} />
    <div><p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p><p className="text-2xl font-bold text-slate-900">{value ?? '—'}</p></div>
  </div>
);

const Field = ({ label, children }) => <div className="flex flex-col gap-1"><span className="text-[11px] font-medium text-slate-500">{label}</span>{children}</div>;

const Filters = ({ f, set, onRun, onExport, loading, exporting }) => (
  <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4" data-testid="taller-audit-filters">
    <Field label="Resultado Auditoría">
      <Select value={f.resultado} onValueChange={(v) => set({ ...f, resultado: v })}>
        <SelectTrigger className="w-48" data-testid="audit-filter-resultado"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="inconsistencias">Solo Inconsistencias</SelectItem>
          <SelectItem value="consistentes">Solo Consistentes</SelectItem>
          <SelectItem value="todos">Todos</SelectItem>
        </SelectContent>
      </Select>
    </Field>
    <Field label="Estatus Equipo">
      <Select value={f.estatus} onValueChange={(v) => set({ ...f, estatus: v })}>
        <SelectTrigger className="w-40" data-testid="audit-filter-estatus"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="all">Todos</SelectItem>{ESTATUS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
      </Select>
    </Field>
    <Field label="Cliente / RIF / Serial">
      <Input className="w-56" value={f.q} onChange={(e) => set({ ...f, q: e.target.value })} onKeyDown={(e) => e.key === 'Enter' && onRun()} placeholder="Buscar..." data-testid="audit-filter-q" />
    </Field>
    <Field label="Fecha de">
      <Select value={f.fecha_campo} onValueChange={(v) => set({ ...f, fecha_campo: v })}>
        <SelectTrigger className="w-40" data-testid="audit-filter-fecha-campo"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="ingreso">Ingreso</SelectItem><SelectItem value="actualizacion">Última actualización</SelectItem></SelectContent>
      </Select>
    </Field>
    <Field label="Desde"><Input type="date" className="w-40" value={f.desde} onChange={(e) => set({ ...f, desde: e.target.value })} data-testid="audit-filter-desde" /></Field>
    <Field label="Hasta"><Input type="date" className="w-40" value={f.hasta} onChange={(e) => set({ ...f, hasta: e.target.value })} data-testid="audit-filter-hasta" /></Field>
    <Button onClick={onRun} disabled={loading} data-testid="audit-run-btn"><Search size={15} className="mr-1.5" />{loading ? 'Consultando…' : 'Consultar'}</Button>
    <Button variant="outline" onClick={onExport} disabled={exporting} data-testid="audit-export-btn"><Download size={15} className="mr-1.5" />{exporting ? 'Exportando…' : 'Exportar Excel'}</Button>
  </div>
);

const Row = ({ r }) => {
  const st = NIVEL_STYLE[r.nivel];
  return (
    <tr className={`border-b border-slate-100 align-top ${st.row}`} data-testid={`audit-row-${r.taller_equipo_id}`}>
      <td className="px-3 py-2 font-mono text-xs text-slate-800">{r.serial}<p className="font-sans text-[11px] text-slate-400">{r.modelo}</p></td>
      <td className="px-3 py-2 text-sm text-slate-800">{r.client_name}<p className="text-[11px] text-slate-500">{r.rif || '—'}</p></td>
      <td className="px-3 py-2 text-sm text-slate-700 whitespace-nowrap">{r.estatus}</td>
      <td className="px-3 py-2 text-xs whitespace-nowrap">{r.quote_number
        ? <><span className="font-mono text-slate-800">{r.quote_number}</span><p className="text-[11px] text-slate-500">{r.quote_status || '—'}{r.quote_historico ? ' · Histórico' : ''}</p></>
        : <span className="text-slate-400">{r.estatus === 'Recibido' ? '-- N/A --' : '-- SIN COTIZ. --'}</span>}</td>
      <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{fmt(r.fecha_ingreso)}</td>
      <td className={`px-3 py-2 text-xs ${st.text}`} data-testid={`audit-diag-${r.taller_equipo_id}`}>
        <span className="inline-flex gap-2"><span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${st.dot}`} />{r.diagnostico}</span>
      </td>
    </tr>
  );
};

export default function TallerAuditoria() {
  const [f, setF] = useState({ resultado: 'inconsistencias', estatus: 'all', q: '', desde: '', hasta: '', fecha_campo: 'ingreso' });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  const params = useCallback(() => {
    const p = { resultado: f.resultado, fecha_campo: f.fecha_campo };
    if (f.estatus !== 'all') p.estatus = f.estatus;
    ['q', 'desde', 'hasta'].forEach((k) => { if (f[k]) p[k] = f[k]; });
    return p;
  }, [f]);

  const run = useCallback(async () => {
    setLoading(true);
    try { setData((await api.get('/reports/taller-audit', { params: params() })).data); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error al consultar la auditoría'); }
    finally { setLoading(false); }
  }, [params]);

  const exportXlsx = async () => {
    setExporting(true);
    try {
      const r = await api.get('/reports/taller-audit/export', { params: params(), responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a'); a.href = url; a.download = `Auditoria_Taller_${new Date().toISOString().slice(0, 10)}.xlsx`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch { toast.error('No se pudo exportar el Excel'); }
    finally { setExporting(false); }
  };

  useEffect(() => { run(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const k = data?.kpis || {};
  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <main className="page-fixed-main flex-1 flex flex-col gap-4 p-6 overflow-hidden" data-testid="taller-audit-page">
        <div className="flex items-center gap-2"><ShieldCheck className="text-indigo-600" /><h1 className="text-2xl font-bold text-slate-900">Auditoría de Taller</h1>
          <span className="text-sm text-slate-500">· Consistencia Equipo vs. Cotización</span></div>
        <Filters f={f} set={setF} onRun={run} onExport={exportXlsx} loading={loading} exporting={exporting} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Kpi icon={ClipboardList} label="Total Auditados" value={k.total} tone="border-slate-200 text-slate-600" testid="audit-kpi-total" />
          <Kpi icon={CheckCircle2} label="Consistentes" value={k.consistentes} tone="border-emerald-200 text-emerald-600" testid="audit-kpi-ok" />
          <Kpi icon={AlertOctagon} label="Inconsistencias" value={k.inconsistencias} tone="border-rose-200 text-rose-600" testid="audit-kpi-bad" />
          <Kpi icon={AlertTriangle} label="Alertas" value={k.alertas} tone="border-amber-200 text-amber-600" testid="audit-kpi-alert" />
        </div>
        <div className="page-scroll-area flex-1 min-h-0 overflow-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left" data-testid="taller-audit-table">
            <thead className="sticky top-0 z-10 bg-slate-800 text-white text-xs">
              <tr>{['Serial / Modelo', 'Cliente (Nombre / RIF)', 'Estatus Equipo', 'Cotización / Estatus', 'Ingreso', 'Diagnóstico de Auditoría'].map((h) => <th key={h} className="px-3 py-2.5 font-semibold">{h}</th>)}</tr>
            </thead>
            <tbody>
              {(data?.rows || []).map((r) => <Row key={r.taller_equipo_id} r={r} />)}
              {data && data.rows.length === 0 && <tr><td colSpan={6} className="py-10 text-center text-sm text-slate-400" data-testid="audit-empty">No hay equipos para los filtros seleccionados.</td></tr>}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
