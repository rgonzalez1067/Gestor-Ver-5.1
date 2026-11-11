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
  const [groupFilter, setGroupFilter] = useState('all');
  const [expanded, setExpanded] = useState({});
  const [dialog, setDialog] = useState({ open: false, id: null });
  const [deleteTarget, setDeleteTarget] = useState(null);

  const fetchBrands = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (groupFilter !== 'all') params.group_id = groupFilter;
      const res = await api.get('/marcas', { params });
      setBrands(res.data || []);
      const ids = new Set((res.data || []).map(b => b.brand_id));
      setSelected(prev => prev.filter(id => ids.has(id)));
    } catch { toast.error('Error al cargar las marcas'); } finally { setLoading(false); }
  };

  useEffect(() => { api.get('/grupos-economicos').then(r => setGroups(r.data || [])).catch(() => {}); }, []);
  useEffect(() => { const t = setTimeout(fetchBrands, 300); return () => clearTimeout(t); /* eslint-disable-next-line */ }, [search, groupFilter]);

  const doDelete = async () => {
    try {
      await api.delete(`/marcas/${deleteTarget.brand_id}`);
      toast.success('Marca eliminada'); setDeleteTarget(null); fetchBrands();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al eliminar'); setDeleteTarget(null); }
  };

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-auto p-8" data-testid="brands-page">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-2"><Tag className="text-teal-600" size={28} /> Marca o Nombre Fantasía</h1>
            <p className="text-slate-500 mt-1">Catálogo de marcas comerciales. Haga clic en una marca para ver sus RIFs y sucursales.</p>
          </div>
          {canEdit && <Button onClick={() => setDialog({ open: true, id: null })} className="bg-indigo-600 hover:bg-indigo-700" data-testid="create-brand-btn"><Plus size={16} className="mr-1.5" /> Nueva Marca</Button>}
        </div>
        <div className="flex gap-3 mb-4">
          <div className="relative max-w-md flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Buscar marca..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9" data-testid="brand-search-input" />
          </div>
          <Select value={groupFilter} onValueChange={setGroupFilter}>
            <SelectTrigger className="w-72" data-testid="brand-group-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los grupos</SelectItem>
              <SelectItem value="_none_">— Sin grupo —</SelectItem>
              {groups.map(g => <SelectItem key={g.group_id} value={g.group_id}>{g.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        {canMass && (
          <div className="flex items-center gap-3 mb-3" data-testid="brand-mass-bar">
            <MassActionsMenu count={selected.length} onPick={setMassAction} actions={BRAND_MASS_ACTIONS} />
            {selected.length > 0 && (
              <button type="button" className="text-xs text-slate-500 hover:underline" data-testid="brand-mass-clear" onClick={() => setSelected([])}>Limpiar selección</button>
            )}
          </div>
        )}
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                {canMass && (
                  <th className="px-3 py-3 w-10">
                    <input type="checkbox" className="h-4 w-4 accent-amber-500" data-testid="brand-mass-select-all"
                      checked={brands.length > 0 && brands.every(b => selected.includes(b.brand_id))}
                      onChange={e => setSelected(e.target.checked ? brands.map(b => b.brand_id) : [])} />
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
                : brands.length === 0 ? <tr><td colSpan={cols} className="text-center py-8 text-slate-400">No hay marcas.</td></tr>
                : brands.map(b => (
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
