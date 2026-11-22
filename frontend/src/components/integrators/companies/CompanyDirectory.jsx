import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Plus, Minus, Search, Building2, AlertTriangle, FileCheck2, IdCard } from 'lucide-react';
import { CompanyFormDialog } from './CompanyFormDialog';
import { CompanyAppsPanel } from './CompanyAppsPanel';
import { MoveAppDialog } from './MoveAppDialog';
import api from '../../../utils/api';
import { toast } from 'sonner';

const PAGE = 60;

const CompanyRow = ({ c, open, onToggle, onOpenFicha }) => (
  <tr className={`border-t border-slate-100 transition-colors ${open ? 'bg-blue-50/50' : 'hover:bg-slate-50'}`} data-testid={`company-row-${c.empresa_id}`}>
    <td className="px-3 py-2.5 w-12">
      <button onClick={onToggle} aria-expanded={open} data-testid={`company-toggle-${c.empresa_id}`}
        className={`h-6 w-6 rounded border inline-flex items-center justify-center transition-colors ${open ? 'bg-brand-blue-600 border-brand-blue-600 text-white' : 'border-slate-300 text-slate-500 hover:border-brand-blue-500 hover:text-brand-blue-600'}`}>
        {open ? <Minus size={13} /> : <Plus size={13} />}
      </button>
    </td>
    <td className="px-3 py-2.5 font-mono text-xs text-slate-600" data-testid={`company-rif-${c.empresa_id}`}>{c.rif || <span className="text-slate-300">— sin RIF —</span>}</td>
    <td className="px-3 py-2.5">
      <button onClick={onOpenFicha} className="text-left text-sm font-semibold text-slate-800 hover:text-brand-blue-600" data-testid={`company-name-${c.empresa_id}`}>{c.razon_social}</button>
      <div className="flex items-center gap-1.5 mt-0.5">
        <span className="text-[10px] text-slate-400">{c.tipo_persona === 'Natural' ? 'Persona Natural' : 'Persona Jurídica'}</span>
        {c.ficha_incompleta && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 inline-flex items-center gap-1" data-testid={`company-incomplete-${c.empresa_id}`}><AlertTriangle size={10} />Ficha incompleta</span>}
        {c.rif_document_url && <span className="text-[10px] text-emerald-600 inline-flex items-center gap-0.5" title="RIF escaneado"><FileCheck2 size={11} />RIF</span>}
      </div>
    </td>
    <td className="px-3 py-2.5 text-sm text-slate-600">{c.principal_contact || '—'}</td>
    <td className="px-3 py-2.5 text-sm"><span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold text-xs" data-testid={`company-app-count-${c.empresa_id}`}>{c.app_count} App{c.app_count === 1 ? '' : 's'}</span></td>
    <td className="px-3 py-2.5 text-right"><Button size="sm" variant="ghost" className="h-7 text-xs" onClick={onOpenFicha} data-testid={`company-ficha-btn-${c.empresa_id}`}><IdCard size={13} className="mr-1" />Ficha</Button></td>
  </tr>
);

export const CompanyDirectory = ({ version, canEdit, onAddApp, onEditApp }) => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [onlyIncomplete, setOnlyIncomplete] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [limit, setLimit] = useState(PAGE);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [moving, setMoving] = useState(null);

  const load = useCallback(async () => {
    try { setCompanies((await api.get('/integrator-companies')).data || []); }
    catch { toast.error('Error al cargar Empresas Integradoras'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load, version]);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    return companies.filter(c => (!onlyIncomplete || c.ficha_incompleta) && (!s || c.razon_social.toLowerCase().includes(s)
      || (c.rif || '').toLowerCase().includes(s) || c.apps.some(a => (a.app_name || '').toLowerCase().includes(s))));
  }, [companies, search, onlyIncomplete]);
  const incomplete = companies.filter(c => c.ficha_incompleta).length;
  const openFicha = (c) => { setEditing(c); setFormOpen(true); };

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden" data-testid="company-directory">
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-slate-200 bg-slate-900 text-white flex-wrap">
        <div className="flex items-center gap-2"><Building2 size={18} /><h2 className="text-sm font-bold uppercase tracking-wider text-white">Directorio de Empresas Integradoras</h2>
          <span className="text-xs text-slate-300" data-testid="company-total">{companies.length} empresas · {incomplete} fichas incompletas</span></div>
        {canEdit && <Button size="sm" className="bg-brand-green-600 hover:bg-brand-green-700 h-8" onClick={() => { setEditing(null); setFormOpen(true); }} data-testid="new-company-btn"><Plus size={14} className="mr-1" />Nueva Empresa Integradora</Button>}
      </div>
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-100">
        <div className="relative flex-1 max-w-md"><Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
          <Input className="pl-8 h-9 text-sm" placeholder="Buscar por empresa, RIF o aplicativo..." value={search} onChange={e => { setSearch(e.target.value); setLimit(PAGE); }} data-testid="company-search" /></div>
        <button type="button" onClick={() => setOnlyIncomplete(v => !v)} aria-pressed={onlyIncomplete} data-testid="company-filter-incomplete"
          className={`h-9 px-3 rounded-md border text-xs font-medium inline-flex items-center gap-1.5 transition-colors ${onlyIncomplete ? 'bg-amber-500 text-white border-amber-600' : 'bg-white text-slate-600 border-slate-200 hover:border-amber-400'}`}>
          <AlertTriangle size={13} /> Fichas incompletas
        </button>
      </div>
      {loading ? <div className="p-8 text-center text-sm text-slate-400">Cargando...</div> : (
        <table className="w-full" data-testid="company-table">
          <thead className="bg-slate-50 text-[11px] uppercase text-slate-500">
            <tr><th className="w-12" /><th className="text-left px-3 py-2 w-40">RIF</th><th className="text-left px-3 py-2">Nombre / Razón Social</th>
              <th className="text-left px-3 py-2">Contacto Principal</th><th className="text-left px-3 py-2 w-28">Aplicativos</th><th className="w-24" /></tr>
          </thead>
          <tbody>
            {filtered.slice(0, limit).map(c => (
              <Fragment key={c.empresa_id}>
                <CompanyRow c={c} open={!!expanded[c.empresa_id]} onToggle={() => setExpanded(p => ({ ...p, [c.empresa_id]: !p[c.empresa_id] }))} onOpenFicha={() => openFicha(c)} />
                {expanded[c.empresa_id] && <tr><td colSpan={6} className="p-0"><CompanyAppsPanel company={c} canEdit={canEdit} onAddApp={onAddApp} onEditApp={onEditApp} onMoveApp={setMoving} /></td></tr>}
              </Fragment>
            ))}
            {!filtered.length && <tr><td colSpan={6} className="p-6 text-center text-sm text-slate-400">Sin resultados</td></tr>}
          </tbody>
        </table>
      )}
      {filtered.length > limit && <div className="p-3 text-center border-t"><Button variant="outline" size="sm" onClick={() => setLimit(l => l + PAGE)} data-testid="company-load-more">Mostrar más ({filtered.length - limit} restantes)</Button></div>}
      <CompanyFormDialog open={formOpen} onOpenChange={setFormOpen} company={editing} onSaved={load} />
      <MoveAppDialog app={moving} companies={companies} onClose={() => setMoving(null)} onMoved={load} />
    </div>
  );
};
