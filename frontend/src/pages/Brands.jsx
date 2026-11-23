import { useState, useEffect, Fragment } from 'react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Plus, Pencil, Trash2, Search, Tag, ChevronRight, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import { usePermission } from '../hooks/usePermission';
import { BrandDialog } from '../components/clients/hierarchy/BrandDialog';
import { RifList } from '../components/clients/hierarchy/HierarchyTree';
import { MassActionsMenu } from '../components/clients/mass/MassActionsMenu';
import { MassActionDialog, BRAND_MASS_ACTIONS } from '../components/clients/mass/MassActionDialog';
import { MultiSelectFilter, NONE_VALUE } from '../components/clients/MultiSelectFilter';
import { BrandsReportButton } from '../components/brands/BrandsReportButton';

export default function Brands() {
  const { canEdit } = usePermission('marcas');
  const { isAdmin, hasSpecial } = usePermission('marcas');
  const canMass = isAdmin || hasSpecial('marcas:mantenimiento_masivo');
  const [selected, setSelected] = useState([]);
  const [massAction, setMassAction] = useState(null);
  const cols = canMass ? 6 : 5;
  const toggle = (id) => setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  const [brands, setBrands] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [groupFilter, setGroupFilter] = useState([]);
  const [ejecutivoFilter, setEjecutivoFilter] = useState([]);
  const [segmentFilter, setSegmentFilter] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [dialog, setDialog] = useState({ open: false, id: null });
  const [deleteTarget, setDeleteTarget] = useState(null);

  const fetchBrands = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      const res = await api.get('/marcas', { params });
      setBrands(res.data || []);
    } catch { toast.error('Error al cargar las marcas'); } finally { setLoading(false); }
  };

  const matches = (vals, filter) => !filter.length || (vals.length ? vals.some(v => filter.includes(v)) : filter.includes(NONE_VALUE));
  const visible = brands.filter(b =>
    matches(b.group_id ? [b.group_id] : [], groupFilter)
    && matches((b.ejecutivos || []).map(e => e.id), ejecutivoFilter)
    && matches(b.segments || [], segmentFilter));
  const ejecutivoOptions = Object.values(Object.fromEntries(brands.flatMap(b => b.ejecutivos || []).map(e => [e.id, { value: e.id, label: e.name }])))
    .sort((a, b) => a.label.localeCompare(b.label));
  const segmentOptions = [...new Set(brands.flatMap(b => b.segments || []))].sort().map(s => ({ value: s, label: s }));
  const groupOptions = groups.map(g => ({ value: g.group_id, label: g.name }));
  const filterSig = `${search}|${groupFilter}|${ejecutivoFilter}|${segmentFilter}|${brands.length}`;
  useEffect(() => {
    const ids = new Set(visible.map(b => b.brand_id));
    setSelected(prev => prev.filter(id => ids.has(id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSig]);

  useEffect(() => { api.get('/grupos-economicos').then(r => setGroups(r.data || [])).catch(() => {}); }, []);
  useEffect(() => { const t = setTimeout(fetchBrands, 300); return () => clearTimeout(t); /* eslint-disable-next-line */ }, [search]);

  const doDelete = async () => {
    try {
      await api.delete(`/marcas/${deleteTarget.brand_id}`);
      toast.success('Marca eliminada'); setDeleteTarget(null); fetchBrands();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al eliminar'); setDeleteTarget(null); }
  };

  return (
    <div className="flex page-fixed-shell bg-slate-50">
      <Sidebar />
      <main className="flex-1 page-fixed-main p-8" data-testid="brands-page">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-2"><Tag className="text-teal-600" size={28} /> Marca o Nombre Fantasía</h1>
            <p className="text-slate-500 mt-1">Catálogo de marcas comerciales. Haga clic en una marca para ver sus RIFs y sucursales.</p>
          </div>
          {canEdit && <Button onClick={() => setDialog({ open: true, id: null })} className="bg-indigo-600 hover:bg-indigo-700" data-testid="create-brand-btn"><Plus size={16} className="mr-1.5" /> Nueva Marca</Button>}
        </div>
        <div className="flex gap-3 mb-4 flex-wrap items-center">
          <div className="relative max-w-md flex-1 min-w-[240px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Buscar marca..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9" data-testid="brand-search-input" />
          </div>
          <MultiSelectFilter label="Grupo" options={groupOptions} selected={groupFilter} onChange={setGroupFilter} testId="brand-group-filter" />
          <MultiSelectFilter label="Ejecutivo" options={ejecutivoOptions} selected={ejecutivoFilter} onChange={setEjecutivoFilter} testId="brand-ejecutivo-filter" />
          <MultiSelectFilter label="Segmento" options={segmentOptions} selected={segmentFilter} onChange={setSegmentFilter} testId="brand-segment-filter" />
          {(groupFilter.length + ejecutivoFilter.length + segmentFilter.length > 0 || search) && (
            <Button variant="ghost" size="sm" className="text-slate-500" data-testid="brand-clear-filters"
              onClick={() => { setSearch(''); setGroupFilter([]); setEjecutivoFilter([]); setSegmentFilter([]); }}>Limpiar filtros</Button>
          )}
          <span className="text-xs text-slate-500 ml-auto" data-testid="brand-visible-count">{visible.length} de {brands.length} marcas</span>
          <BrandsReportButton brandIds={visible.map(b => b.brand_id)} filtersLabel={[
            search && `Búsqueda "${search}"`,
            groupFilter.length && `Grupo (${groupFilter.length})`,
            ejecutivoFilter.length && `Ejecutivo: ${ejecutivoFilter.map(v => ejecutivoOptions.find(o => o.value === v)?.label || 'Sin asignar').join(', ')}`,
            segmentFilter.length && `Segmento: ${segmentFilter.map(v => v === NONE_VALUE ? 'Sin asignar' : v).join(', ')}`,
          ].filter(Boolean).join(' · ')} />
        </div>
        {canMass && (
          <div className="flex items-center gap-3 mb-3" data-testid="brand-mass-bar">
            <MassActionsMenu count={selected.length} onPick={setMassAction} actions={BRAND_MASS_ACTIONS} />
            {selected.length > 0 && (
              <button type="button" className="text-xs text-slate-500 hover:underline" data-testid="brand-mass-clear" onClick={() => setSelected([])}>Limpiar selección</button>
            )}
          </div>
        )}
        <div className="bg-white rounded-lg border border-slate-200 page-scroll-area">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                {canMass && (
                  <th className="px-3 py-3 w-10">
                    <input type="checkbox" className="h-4 w-4 accent-amber-500" data-testid="brand-mass-select-all"
                      checked={visible.length > 0 && visible.every(b => selected.includes(b.brand_id))}
                      onChange={e => setSelected(e.target.checked ? visible.map(b => b.brand_id) : [])} />
                  </th>
                )}
                <th className="text-left px-4 py-3">Marca / Nombre Fantasía</th>
                <th className="text-left px-4 py-3">Grupo Económico</th>
                <th className="text-center px-4 py-3">RIFs</th>
                <th className="text-center px-4 py-3">Contactos</th>
                <th className="text-right px-4 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? <tr><td colSpan={cols} className="text-center py-8 text-slate-400">Cargando...</td></tr>
                : visible.length === 0 ? <tr><td colSpan={cols} className="text-center py-8 text-slate-400" data-testid="brand-empty">{brands.length ? 'Ninguna marca coincide con los filtros.' : 'No hay marcas.'}</td></tr>
                : visible.map(b => (
                  <Fragment key={b.brand_id}>
                    <tr className={`border-t hover:bg-slate-50 ${selected.includes(b.brand_id) ? 'bg-amber-50/60' : ''}`} data-testid={`brand-row-${b.brand_id}`}>
                      {canMass && (
                        <td className="px-3 py-3">
                          <input type="checkbox" className="h-4 w-4 accent-amber-500" data-testid={`brand-mass-select-${b.brand_id}`}
                            checked={selected.includes(b.brand_id)} onChange={() => toggle(b.brand_id)} />
                        </td>
                      )}
                      <td className="px-4 py-3">
                        <button type="button" onClick={() => setExpanded(p => ({ ...p, [b.brand_id]: !p[b.brand_id] }))}
                          className="flex items-center gap-2 font-medium text-slate-800 hover:text-indigo-700" data-testid={`brand-expand-${b.brand_id}`}>
                          {expanded[b.brand_id] ? <ChevronDown size={15} /> : <ChevronRight size={15} />}{b.name}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-slate-500">{b.group_name || '—'}</td>
                      <td className="px-4 py-3 text-center"><span className="inline-flex min-w-[28px] justify-center px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-semibold" data-testid={`brand-rif-count-${b.brand_id}`}>{b.rif_count}</span></td>
                      <td className="px-4 py-3 text-center text-slate-600">{b.contacts_count}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => setDialog({ open: true, id: b.brand_id })} title="Editar" data-testid={`brand-edit-${b.brand_id}`}><Pencil size={15} className="text-slate-500" /></Button>
                          {canEdit && <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => setDeleteTarget(b)} title="Eliminar" data-testid={`brand-delete-${b.brand_id}`}><Trash2 size={15} className="text-red-500" /></Button>}
                        </div>
                      </td>
                    </tr>
                    {expanded[b.brand_id] && (
                      <tr className="bg-slate-50/60" data-testid={`brand-tree-${b.brand_id}`}><td colSpan={cols} className="px-6 py-2"><RifList brandId={b.brand_id} /></td></tr>
                    )}
                  </Fragment>
                ))}
            </tbody>
          </table>
        </div>
        {canMass && massAction && (
          <MassActionDialog scope="brands" action={massAction} clientIds={selected} onClose={() => setMassAction(null)}
            onDone={() => { fetchBrands(); setSelected([]); }} />
        )}
        <BrandDialog open={dialog.open} brandId={dialog.id} editable={canEdit} onClose={() => setDialog({ open: false, id: null })} onSaved={fetchBrands} />
        <AlertDialog open={!!deleteTarget} onOpenChange={o => !o && setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Eliminar Marca</AlertDialogTitle>
              <AlertDialogDescription>¿Eliminar "{deleteTarget?.name}"? Solo es posible si no tiene RIFs asociados.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={doDelete} className="bg-red-600 hover:bg-red-700" data-testid="confirm-delete-brand">Eliminar</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </main>
    </div>
  );
}
