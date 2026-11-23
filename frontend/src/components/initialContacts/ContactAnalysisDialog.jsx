import { useCallback, useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { FileSpreadsheet, FileText, Loader2, RotateCcw } from 'lucide-react';
import { AnalysisKpis } from './AnalysisKpis';
import { AnalysisTable } from './AnalysisTable';
import { referenteLabel } from '../referentes/ReferentePicker';
import { toast } from 'sonner';
import api from '../../utils/api';

const EMPTY = { referente_id: '', date_from: '', date_to: '', assigned_to: '', sede: '', status: '' };
const SEDES = [['', 'Todos'], ['PYME', 'Pyme'], ['CORP', 'Corporativo']];
const STATUSES = [['', 'Todos'], ['active', 'En Gestión'], ['converted', 'Convertido a Cliente'], ['closed', 'Cerrado']];
const sel = 'h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm';

const Field = ({ label, children }) => <div className="min-w-0"><Label className="text-[11px] uppercase text-slate-500">{label}</Label>{children}</div>;

export const ContactAnalysisDialog = ({ open, onClose }) => {
  const [f, setF] = useState(EMPTY);
  const [data, setData] = useState(null);
  const [referentes, setReferentes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState('');
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  const load = useCallback(() => {
    setLoading(true);
    api.get('/initial-contacts-report', { params: f }).then((r) => setData(r.data))
      .catch((e) => toast.error(e.response?.data?.detail || 'Error al generar el reporte')).finally(() => setLoading(false));
  }, [f]);
  useEffect(() => { if (open) load(); }, [open, load]);
  useEffect(() => { if (open) api.get('/referentes', { params: { include_inactive: true } }).then((r) => setReferentes(r.data.items)).catch(() => {}); }, [open]);

  const filtersLabel = () => [
    f.referente_id && `Referente: ${referentes.find((r) => r.referente_id === f.referente_id)?.nombre_referente || ''}`,
    (f.date_from || f.date_to) && `Periodo: ${f.date_from || '…'} a ${f.date_to || '…'}`,
    f.assigned_to && `Asignado: ${data?.assignees.find((a) => a.user_id === f.assigned_to)?.name || ''}`,
    f.sede && `Segmento: ${SEDES.find(([k]) => k === f.sede)[1]}`,
    f.status && `Estatus: ${STATUSES.find(([k]) => k === f.status)[1]}`,
  ].filter(Boolean).join(' · ');

  const download = async (format) => {
    setExporting(format);
    try {
      const res = await api.get('/initial-contacts-report/export', { params: { ...f, format, filters_label: filtersLabel() }, responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url; a.download = `Analisis_Contactos_${new Date().toISOString().slice(0, 10)}.${format}`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Error al exportar'); }
    finally { setExporting(''); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-7xl w-[96vw] h-[92vh] flex flex-col gap-3" data-testid="contact-analysis-dialog">
        <DialogHeader className="flex-row items-center justify-between space-y-0 pr-8">
          <DialogTitle className="text-xl">Análisis de la Gestión de Contactos</DialogTitle>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={!!exporting} onClick={() => download('xlsx')} data-testid="analysis-export-xlsx">
              {exporting === 'xlsx' ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <FileSpreadsheet size={14} className="mr-1.5 text-emerald-600" />}Excel</Button>
            <Button size="sm" variant="outline" disabled={!!exporting} onClick={() => download('pdf')} data-testid="analysis-export-pdf">
              {exporting === 'pdf' ? <Loader2 size={14} className="mr-1.5 animate-spin" /> : <FileText size={14} className="mr-1.5 text-red-600" />}PDF</Button>
          </div>
        </DialogHeader>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 items-end" data-testid="analysis-filters">
          <Field label="Referente"><select className={sel} value={f.referente_id} onChange={set('referente_id')} data-testid="analysis-filter-referente">
            <option value="">Todos</option>{referentes.map((r) => <option key={r.referente_id} value={r.referente_id}>{referenteLabel(r)}</option>)}</select></Field>
          <Field label="Desde"><Input type="date" className="h-9" value={f.date_from} onChange={set('date_from')} data-testid="analysis-filter-from" /></Field>
          <Field label="Hasta"><Input type="date" className="h-9" value={f.date_to} onChange={set('date_to')} data-testid="analysis-filter-to" /></Field>
          <Field label="Asignado a"><select className={sel} value={f.assigned_to} onChange={set('assigned_to')} data-testid="analysis-filter-assigned">
            <option value="">Todos</option>{(data?.assignees || []).map((a) => <option key={a.user_id} value={a.user_id}>{a.name}</option>)}</select></Field>
          <Field label="Segmento"><select className={sel} value={f.sede} onChange={set('sede')} data-testid="analysis-filter-sede">
            {SEDES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Field label="Estatus"><select className={sel} value={f.status} onChange={set('status')} data-testid="analysis-filter-status">
            {STATUSES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Button variant="ghost" size="sm" className="h-9" onClick={() => setF(EMPTY)} data-testid="analysis-filter-clear"><RotateCcw size={14} className="mr-1.5" />Limpiar</Button>
        </div>
        <AnalysisKpis kpis={data?.kpis} />
        <div className="flex-1 min-h-0 overflow-auto border border-slate-200 rounded-lg relative" data-testid="analysis-scroll-area">
          {loading && <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10"><Loader2 className="animate-spin text-slate-400" /></div>}
          {data && <AnalysisTable items={data.items} />}
        </div>
      </DialogContent>
    </Dialog>
  );
};
