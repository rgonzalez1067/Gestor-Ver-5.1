import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { FileText, FileSpreadsheet, Search } from 'lucide-react';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { MultiPick } from './MultiPick';

const TIPOS = [['VPOS', 'VPOS'], ['MPOS', 'MPOS'], ['GATEWAY', 'Payment Gateway'], ['LINK', 'Link de Pago']];
const EMPTY = { implementador: [], generador: [], desde: '', hasta: '', tipo: '', estatus: '', nivel: '' };
const NIVELES = [['critico', 'Retraso Crítico'], ['medio', 'Retraso Medio'], ['al_dia', 'Al Día']];
const LEVEL_CLS = { critico: 'bg-rose-100 text-rose-700', medio: 'bg-amber-100 text-amber-700', al_dia: 'bg-emerald-100 text-emerald-700' };
const fmt = (d) => (d ? String(d).slice(0, 10).split('-').reverse().join('/') : '—');

const Pick = ({ label, value, onChange, options, testid }) => (
  <div className="flex flex-col gap-1">
    <span className="text-[11px] font-medium text-slate-500">{label}</span>
    <Select value={value || 'all'} onValueChange={(v) => onChange(v === 'all' ? '' : v)}>
      <SelectTrigger className="h-9" data-testid={testid}><SelectValue /></SelectTrigger>
      <SelectContent><SelectItem value="all">Todos</SelectItem>{options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
    </Select>
  </div>
);

const label = (f) => [f.implementador.length && `Implementador: ${f.implementador.join(', ')}`, f.generador.length && `Generador: ${f.generador.join(', ')}`,
  (f.desde || f.hasta) && `Envío: ${fmt(f.desde) || '…'} a ${fmt(f.hasta) || '…'}`,
  f.tipo && `Tipo: ${TIPOS.find((t) => t[0] === f.tipo)?.[1]}`, f.estatus && `Estatus: ${f.estatus}`, f.nivel && `Tipo de Retraso: ${NIVELES.find((n) => n[0] === f.nivel)?.[1]}`].filter(Boolean).join(' · ');

export const ProjectFollowupReportDialog = ({ open, onOpenChange }) => {
  const [f, setF] = useState(EMPTY);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState('');
  const [applied, setApplied] = useState(EMPTY);

  const params = (src) => Object.fromEntries(Object.entries(src).map(([k, v]) => [k, Array.isArray(v) ? v.join('||') : v]).filter(([, v]) => v));
  const run = useCallback(async (src = f) => {
    setBusy('run');
    try { setData((await api.get('/projects-report/followup', { params: params(src) })).data); setApplied(src); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error al generar el reporte'); }
    finally { setBusy(''); }
  }, [f]);
  useEffect(() => { if (open) run(); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const exportAs = async (format) => {
    setBusy(format);
    try {
      const r = await api.get('/projects-report/followup/export', { params: { ...params(applied), format, filters_label: label(applied) }, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      if (format === 'pdf') window.open(url, '_blank');
      else { const a = document.createElement('a'); a.href = url; a.download = `Seguimiento_Proyectos_${new Date().toISOString().slice(0, 10)}.xlsx`; a.click(); }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch { toast.error('No se pudo generar el archivo'); }
    finally { setBusy(''); }
  };

  const o = data?.options || { implementadores: [], generadores: [], estatus: [] };
  const k = data?.kpis || {};
  const set = (key) => (v) => setF((p) => ({ ...p, [key]: v }));
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[1500px] w-[97vw] max-h-[92vh] flex flex-col gap-3" data-testid="followup-report-dialog">
        <DialogHeader>
          <DialogTitle>Reporte de Seguimiento de Proyectos</DialogTitle>
          <DialogDescription>Seleccione los filtros y genere el informe en PDF o Excel.</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 md:grid-cols-7 gap-3 items-end">
          <MultiPick label="Implementador" value={f.implementador} onChange={set('implementador')} options={o.implementadores} testid="followup-filter-implementador" />
          <MultiPick label="Generador" value={f.generador} onChange={set('generador')} options={o.generadores} testid="followup-filter-generador" />
          <div className="flex flex-col gap-1"><span className="text-[11px] font-medium text-slate-500">Envío desde</span><Input type="date" className="h-9" value={f.desde} onChange={(e) => set('desde')(e.target.value)} data-testid="followup-filter-desde" /></div>
          <div className="flex flex-col gap-1"><span className="text-[11px] font-medium text-slate-500">Envío hasta</span><Input type="date" className="h-9" value={f.hasta} onChange={(e) => set('hasta')(e.target.value)} data-testid="followup-filter-hasta" /></div>
          <Pick label="Tipo de Proyecto" value={f.tipo} onChange={set('tipo')} options={TIPOS} testid="followup-filter-tipo" />
          <Pick label="Estatus" value={f.estatus} onChange={set('estatus')} options={o.estatus.map((x) => [x, x])} testid="followup-filter-estatus" />
          <Pick label="Tipo de Retraso" value={f.nivel} onChange={set('nivel')} options={NIVELES} testid="followup-filter-nivel" />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" onClick={() => run()} disabled={!!busy} data-testid="followup-run-btn"><Search size={14} className="mr-1.5" />{busy === 'run' ? 'Consultando…' : 'Aplicar filtros'}</Button>
          <Button size="sm" variant="ghost" onClick={() => { setF(EMPTY); run(EMPTY); }} data-testid="followup-clear-btn">Limpiar</Button>
          <div className="flex-1" />
          <span className="text-xs text-slate-600" data-testid="followup-kpis">
            {k.total ?? 0} proyectos · <b className="text-rose-600">{k.critico ?? 0} críticos</b> · <b className="text-amber-600">{k.medio ?? 0} medios</b> · <b className="text-emerald-600">{k.al_dia ?? 0} al día</b> · Avance prom. {k.avance_promedio ?? 0}%
          </span>
          <Button size="sm" className="bg-rose-600 hover:bg-rose-700" onClick={() => exportAs('pdf')} disabled={!!busy || !data} data-testid="followup-pdf-btn"><FileText size={14} className="mr-1.5" />{busy === 'pdf' ? 'Generando…' : 'Generar PDF'}</Button>
          <Button size="sm" variant="outline" className="border-emerald-300 text-emerald-700" onClick={() => exportAs('xlsx')} disabled={!!busy || !data} data-testid="followup-xlsx-btn"><FileSpreadsheet size={14} className="mr-1.5" />{busy === 'xlsx' ? 'Exportando…' : 'Exportar Excel'}</Button>
        </div>
        <div className="flex-1 min-h-0 overflow-auto rounded-lg border border-slate-200">
          <table className="w-full text-xs" data-testid="followup-table">
            <thead className="sticky top-0 bg-slate-800 text-white">
              <tr>{['Proyecto', 'Cliente', '% Avance', 'Asignación', 'Generador', 'Implementador', 'Estado', 'Responsable', 'Últ. Seguimiento', 'Días', 'Tipo de Retraso'].map((h) => <th key={h} className="px-2 py-2 text-left font-semibold whitespace-nowrap">{h}</th>)}</tr>
            </thead>
            <tbody>
              {(data?.rows || []).map((r) => (
                <tr key={r.project_id} className="border-b border-slate-100" data-testid={`followup-row-${r.project_id}`}>
                  <td className="px-2 py-1.5 font-mono whitespace-nowrap">{r.project_number}<p className="font-sans text-[10px] text-slate-400">{r.tipo}</p></td>
                  <td className="px-2 py-1.5 max-w-[170px] truncate" title={r.cliente}>{r.cliente}</td>
                  <td className="px-2 py-1.5"><div className="flex items-center gap-1.5"><div className="h-1.5 w-12 rounded bg-slate-200"><div className="h-1.5 rounded bg-blue-600" style={{ width: `${r.avance}%` }} /></div>{r.avance}%</div></td>
                  <td className="px-2 py-1.5 whitespace-nowrap">{fmt(r.fecha_asignacion)}</td>
                  <td className="px-2 py-1.5 whitespace-nowrap">{r.generador}</td>
                  <td className="px-2 py-1.5 whitespace-nowrap">{r.implementador}</td>
                  <td className="px-2 py-1.5 whitespace-nowrap">{r.estado}</td>
                  <td className="px-2 py-1.5">{r.responsable}</td>
                  <td className="px-2 py-1.5 whitespace-nowrap">{fmt(r.ultimo_seguimiento)}</td>
                  <td className="px-2 py-1.5 text-right font-semibold">{r.dias_retraso}</td>
                  <td className="px-2 py-1.5"><span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold whitespace-nowrap ${LEVEL_CLS[r.nivel]}`}>{r.nivel_label}</span></td>
                </tr>
              ))}
              {data && !data.rows.length && <tr><td colSpan={11} className="py-8 text-center text-slate-400" data-testid="followup-empty">No hay proyectos para los filtros seleccionados.</td></tr>}
            </tbody>
          </table>
        </div>
      </DialogContent>
    </Dialog>
  );
};
