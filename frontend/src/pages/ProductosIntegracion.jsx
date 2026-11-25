import { useEffect, useMemo, useState } from 'react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Plus, Pencil, Search, Boxes, Trash2, ArrowUpDown, ArrowDown, ArrowUp } from 'lucide-react';
import { ProductoFormDialog } from '../components/productosIntegracion/ProductoFormDialog';
import { toast } from 'sonner';
import api from '../utils/api';

export default function ProductosIntegracion() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [sort, setSort] = useState({ key: '', dir: 'desc' });

  const load = () => api.get('/productos-integracion').then((r) => setItems(r.data))
    .catch(() => toast.error('Error al cargar productos')).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    const rows = items.filter((p) => !s || `${p.codigo} ${p.nombre}`.toLowerCase().includes(s));
    if (!sort.key) return rows;
    return [...rows].sort((a, b) => (sort.dir === 'desc' ? b[sort.key] - a[sort.key] : a[sort.key] - b[sort.key]));
  }, [items, search, sort]);
  const sortBy = (key) => setSort((s) => (s.key !== key ? { key, dir: 'desc' } : s.dir === 'desc' ? { key, dir: 'asc' } : { key: '', dir: 'desc' }));
  const SortIcon = ({ k }) => (sort.key !== k ? <ArrowUpDown size={11} className="opacity-50" /> : sort.dir === 'desc' ? <ArrowDown size={11} /> : <ArrowUp size={11} />);

  const toggle = async (p) => {
    try { await api.put(`/productos-integracion/${p.producto_id}`, { activo: !p.activo }); toast.success(p.activo ? 'Producto inactivado' : 'Producto activado'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
  };
  const confirmDelete = async () => {
    try { const { data } = await api.delete(`/productos-integracion/${deleting.producto_id}`); toast.success(data.message); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error al eliminar'); }
    finally { setDeleting(null); }
  };

  return (
    <div className="flex page-fixed-shell bg-slate-50">
      <Sidebar />
      <main className="flex-1 page-fixed-main" data-testid="productos-integracion-page">
        <div className="max-w-6xl mx-auto p-6 lg:p-8 page-fixed-main w-full">
          <div className="flex items-center justify-between gap-4 mb-5">
            <h1 className="text-3xl font-bold text-slate-900 font-manrope flex items-center gap-3"><Boxes className="text-brand-blue-600" size={28} />Productos para Integración</h1>
            <Button onClick={() => { setEditing(null); setFormOpen(true); }} className="bg-brand-green-600 hover:bg-brand-green-700" data-testid="productos-new-btn"><Plus size={16} className="mr-2" />Nuevo Producto</Button>
          </div>
          <div className="flex items-center gap-3 mb-4">
            <div className="relative w-72"><Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
              <Input className="pl-8 h-9" placeholder="Buscar por código o nombre..." value={search} onChange={(e) => setSearch(e.target.value)} data-testid="productos-search" /></div>
            <span className="text-xs text-slate-500" data-testid="productos-count">{filtered.length} producto(s) · los activos alimentan la Matriz de Productos del Integrador</span>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 page-scroll-area" data-testid="productos-scroll-area">
            {loading ? <p className="p-8 text-center text-sm text-slate-400">Cargando...</p> : (
              <table className="w-full text-sm" data-testid="productos-table">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>
                  <th className="px-3 py-3 text-center w-16">Orden</th><th className="px-3 py-3 text-left">Código</th><th className="px-3 py-3 text-left">Nombre</th>
                  <th className="px-3 py-3 text-left">Descripción</th><th className="px-3 py-3 text-center"><button type="button" onClick={() => sortBy('certificados')} className="inline-flex items-center gap-1 uppercase hover:text-slate-800" title="Aplicativos con el producto Certificado (C)" data-testid="productos-sort-certificados">Certificados (C)<SortIcon k="certificados" /></button></th>
                  <th className="px-3 py-3 text-center"><button type="button" onClick={() => sortBy('en_proceso')} className="inline-flex items-center gap-1 uppercase hover:text-slate-800" title="Aplicativos con el producto Pendiente (P)" data-testid="productos-sort-pendientes">Pendientes (P)<SortIcon k="en_proceso" /></button></th><th className="px-3 py-3 text-center">Activo</th><th className="px-3 py-3 w-20" />
                </tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((p) => (
                    <tr key={p.producto_id} className={`hover:bg-slate-50 ${p.activo ? '' : 'opacity-60'}`} data-testid={`producto-row-${p.producto_id}`}>
                      <td className="px-3 py-2 text-center text-slate-500">{p.orden_despliegue ?? '—'}</td>
                      <td className="px-3 py-2 font-mono text-xs text-slate-600">{p.codigo}</td>
                      <td className="px-3 py-2 font-medium text-slate-800">{p.nombre}</td>
                      <td className="px-3 py-2 text-slate-500 text-xs max-w-[280px] truncate" title={p.descripcion}>{p.descripcion || '—'}</td>
                      <td className="px-3 py-2 text-center font-semibold text-emerald-700" data-testid={`producto-certificados-${p.producto_id}`}>{p.certificados}</td>
                      <td className="px-3 py-2 text-center text-amber-700" data-testid={`producto-pendientes-${p.producto_id}`}>{p.en_proceso}</td>
                      <td className="px-3 py-2 text-center"><Switch checked={p.activo} onCheckedChange={() => toggle(p)} data-testid={`producto-status-${p.producto_id}`} /></td>
                      <td className="px-3 py-2"><div className="flex items-center gap-3">
                        <button type="button" onClick={() => { setEditing(p); setFormOpen(true); }} className="text-slate-400 hover:text-brand-blue-600" title="Editar" data-testid={`producto-edit-${p.producto_id}`}><Pencil size={15} /></button>
                        <button type="button" onClick={() => setDeleting(p)} className="text-slate-400 hover:text-red-600" title="Eliminar" data-testid={`producto-delete-${p.producto_id}`}><Trash2 size={15} /></button>
                      </div></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>
      <ProductoFormDialog open={formOpen} producto={editing} onClose={() => setFormOpen(false)} onSaved={load} />
      <AlertDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent data-testid="producto-delete-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar Producto</AlertDialogTitle>
            <AlertDialogDescription>Se eliminará «{deleting?.nombre}» del catálogo y dejará de verse en la Matriz. {deleting?.aplicativos ? `Hoy lo usan ${deleting.aplicativos} aplicativo(s) (${deleting.certificados} certificados, ${deleting.en_proceso} pendientes). ` : ''}Los certificados ya emitidos conservan su histórico. Si solo quiere ocultarlo, use el interruptor Activo.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="producto-delete-cancel">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-red-600 hover:bg-red-700" data-testid="producto-delete-confirm">Eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
