import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ScrollText, Download, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { AuditFilters } from '../components/audit/AuditFilters';
import { AuditTable } from '../components/audit/AuditTable';
import { AuditDetailDialog } from '../components/audit/AuditDetailDialog';
import { EMPTY_FILTERS, toParams } from '../components/audit/auditUtils';

const PAGE_SIZE = 50;

const Pager = ({ page, total, onPage }) => {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <div className="flex items-center justify-end gap-2 text-sm" data-testid="audit-pager">
      <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)} data-testid="audit-prev-page">Anterior</Button>
      <span className="text-slate-600" data-testid="audit-page-indicator">Página {page} de {pages.toLocaleString('es-VE')}</span>
      <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)} data-testid="audit-next-page">Siguiente</Button>
    </div>
  );
};

export default function AuditTrailsPage() {
  const navigate = useNavigate();
  const isAdmin = (() => { try { return JSON.parse(localStorage.getItem('user') || '{}')?.role === 'admin'; } catch { return false; } })();
  const [options, setOptions] = useState({ modules: [], users: [] });
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [applied, setApplied] = useState(EMPTY_FILTERS);
  const [data, setData] = useState({ items: [], total: 0, total_all: 0 });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [detail, setDetail] = useState(null);

  useEffect(() => { api.get('/audit-trails/filters').then((r) => setOptions(r.data)).catch(() => {}); }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get('/audit-trails', { params: { ...toParams(applied), page, page_size: PAGE_SIZE } });
      setData(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudieron cargar las pistas');
    } finally { setLoading(false); }
  }, [applied, page]);

  useEffect(() => { load(); }, [load]);

  const search = () => { setPage(1); setApplied(filters); };
  const reset = () => { setFilters(EMPTY_FILTERS); setPage(1); setApplied(EMPTY_FILTERS); };
  const view = async (id) => {
    try { setDetail((await api.get(`/audit-trails/${id}`)).data); } catch { toast.error('No se pudo abrir el detalle'); }
  };
  const exportXlsx = async () => {
    setExporting(true);
    try {
      const r = await api.get('/audit-trails/export', { params: toParams(applied), responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url; a.download = `pistas_auditoria_${new Date().toISOString().slice(0, 10)}.xlsx`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('No se pudo exportar'); } finally { setExporting(false); }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 p-6 lg:p-8 space-y-5 min-w-0" data-testid="audit-trails-page">
        <button onClick={() => navigate(isAdmin ? '/settings/security' : '/settings')} className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1" data-testid="audit-back-btn"><ArrowLeft size={14} />{isAdmin ? 'Seguridad y Control de Acceso' : 'Configuración'}</button>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-[#003366] text-white flex items-center justify-center"><ScrollText size={22} /></div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 font-manrope">Pistas de Auditoría Global</h1>
              <p className="text-sm text-slate-500">Registro inmutable de creaciones, modificaciones y eliminaciones (excepto Proyectos, que usa su Bitácora). Se conserva 2 años.</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-[11px] uppercase tracking-wide text-slate-400">Total registros auditados</p>
              <p className="text-2xl font-bold text-[#003366]" data-testid="audit-total-all">{(data.total_all || 0).toLocaleString('es-VE')}</p>
            </div>
            <Button variant="outline" onClick={exportXlsx} disabled={exporting} data-testid="audit-export-btn">
              {exporting ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Download size={14} className="mr-1" />}Exportar a Excel
            </Button>
          </div>
        </div>
        <AuditFilters options={options} filters={filters} setFilters={setFilters} onSearch={search} onReset={reset} />
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-600" data-testid="audit-total-filtered">{(data.total || 0).toLocaleString('es-VE')} resultado(s)</p>
          <Pager page={page} total={data.total} onPage={setPage} />
        </div>
        <AuditTable items={data.items} loading={loading} onView={view} />
        <AuditDetailDialog trail={detail} onClose={() => setDetail(null)} />
      </main>
    </div>
  );
}
