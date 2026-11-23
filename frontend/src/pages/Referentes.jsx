import { useEffect, useMemo, useState } from 'react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import { Plus, Pencil, Search, UserCheck, GitMerge, Trash2 } from 'lucide-react';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { ReferenteFormDialog } from '../components/referentes/ReferenteFormDialog';
import { MergeReferentesDialog } from '../components/referentes/MergeReferentesDialog';
import { TIPOS_REFERENTE } from '../components/referentes/ReferentePicker';
import { formatDate } from '../utils/dateFormat';
import { toast } from 'sonner';
import api from '../utils/api';

const TIPO_LABEL = Object.fromEntries(TIPOS_REFERENTE);
const TIPO_STYLE = { PERSONA: 'bg-sky-50 text-sky-700', AREA: 'bg-amber-50 text-amber-700', EMPRESA: 'bg-violet-50 text-violet-700' };

export default function Referentes() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [editing, setEditing] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [checked, setChecked] = useState([]);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [deleting, setDeleting] = useState(null);

  const load = () => api.get('/referentes', { params: { include_inactive: true } })
    .then((r) => setItems(r.data.items)).catch(() => toast.error('Error al cargar referentes')).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    return items.filter((r) => (status === 'all' || (status === 'active' ? r.estatus : !r.estatus))
      && (!s || `${r.nombre_referente} ${r.empresa} ${r.persona}`.toLowerCase().includes(s)));
  }, [items, search, status]);

  const toggleStatus = async (r) => {
    try { await api.put(`/referentes/${r.referente_id}`, { estatus: !r.estatus }); toast.success(r.estatus ? 'Referente inactivado' : 'Referente activado'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
  };
  const confirmDelete = async () => {
    try { const { data } = await api.delete(`/referentes/${deleting.referente_id}`); toast.success(data.message); setChecked((c) => c.filter((x) => x !== deleting.referente_id)); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error al eliminar'); }
    finally { setDeleting(null); }
  };
  const toggleCheck = (id) => setChecked((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]));
  const selected = items.filter((r) => checked.includes(r.referente_id));

  return (
    <div className="flex page-fixed-shell bg-slate-50">
      <Sidebar />
      <main className="flex-1 page-fixed-main" data-testid="referentes-page">
        <div className="max-w-6xl mx-auto p-6 lg:p-8 page-fixed-main w-full">
          <div className="flex items-center justify-between gap-4 mb-5">
            <h1 className="text-3xl font-bold text-slate-900 font-manrope flex items-center gap-3"><UserCheck className="text-brand-blue-600" size={28} />Referentes</h1>
            <div className="flex gap-2">
              <Button variant="outline" disabled={checked.length < 2} onClick={() => setMergeOpen(true)} data-testid="referentes-merge-btn"><GitMerge size={16} className="mr-2" />Fusionar ({checked.length})</Button>
              <Button onClick={() => { setEditing(null); setFormOpen(true); }} className="bg-brand-green-600 hover:bg-brand-green-700" data-testid="referentes-new-btn"><Plus size={16} className="mr-2" />Nuevo Referente</Button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <div className="relative w-72"><Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
              <Input className="pl-8 h-9" placeholder="Buscar por nombre, empresa o persona..." value={search} onChange={(e) => setSearch(e.target.value)} data-testid="referentes-search" /></div>
            <select className="h-9 rounded-md border border-slate-200 bg-white px-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="referentes-status-filter">
              <option value="all">Todos</option><option value="active">Activos</option><option value="inactive">Inactivos</option>
            </select>
            <span className="text-xs text-slate-500" data-testid="referentes-count">{filtered.length} referente(s)</span>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 page-scroll-area" data-testid="referentes-scroll-area">
            {loading ? <p className="p-8 text-center text-sm text-slate-400">Cargando...</p> : filtered.length === 0 ? <p className="p-8 text-center text-sm text-slate-400">No hay referentes</p> : (
              <table className="w-full text-sm" data-testid="referentes-table">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr><th className="w-10 px-3 py-3" /><th className="px-3 py-3 text-left">Nombre</th><th className="px-3 py-3 text-left">Tipo</th><th className="px-3 py-3 text-left">Empresa</th><th className="px-3 py-3 text-left">Persona</th><th className="px-3 py-3 text-center">Contactos</th><th className="px-3 py-3 text-left">Creado</th><th className="px-3 py-3 text-center">Activo</th><th className="px-3 py-3 w-20" /></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((r) => (
                    <tr key={r.referente_id} className={`hover:bg-slate-50 ${r.estatus ? '' : 'opacity-60'}`} data-testid={`referente-row-${r.referente_id}`}>
                      <td className="px-3 py-2 text-center"><input type="checkbox" checked={checked.includes(r.referente_id)} onChange={() => toggleCheck(r.referente_id)} data-testid={`referente-check-${r.referente_id}`} /></td>
                      <td className="px-3 py-2 font-medium text-slate-800">{r.nombre_referente}</td>
                      <td className="px-3 py-2"><span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${TIPO_STYLE[r.tipo_referente]}`}>{TIPO_LABEL[r.tipo_referente]}</span></td>
                      <td className="px-3 py-2 text-slate-600">{r.empresa || '—'}</td>
                      <td className="px-3 py-2 text-slate-600">{r.persona || '—'}</td>
                      <td className="px-3 py-2 text-center text-slate-700" data-testid={`referente-contacts-${r.referente_id}`}>{r.contactos}</td>
                      <td className="px-3 py-2 text-slate-500 text-xs">{formatDate(r.fecha_creacion)}</td>
                      <td className="px-3 py-2 text-center"><Switch checked={r.estatus} onCheckedChange={() => toggleStatus(r)} data-testid={`referente-status-${r.referente_id}`} /></td>
                      <td className="px-3 py-2"><div className="flex items-center gap-3">
                        <button type="button" onClick={() => { setEditing(r); setFormOpen(true); }} className="text-slate-400 hover:text-brand-blue-600" title="Editar" data-testid={`referente-edit-${r.referente_id}`}><Pencil size={15} /></button>
                        <button type="button" disabled={r.contactos > 0} onClick={() => setDeleting(r)} className="text-slate-400 hover:text-red-600 disabled:opacity-30 disabled:hover:text-slate-400 disabled:cursor-not-allowed" title={r.contactos > 0 ? `No se puede eliminar: tiene ${r.contactos} contacto(s) vinculado(s). Fusiónelo o inactívelo.` : 'Eliminar'} data-testid={`referente-delete-${r.referente_id}`}><Trash2 size={15} /></button>
                      </div></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>
      <ReferenteFormDialog open={formOpen} referente={editing} onClose={() => setFormOpen(false)} onSaved={load} />
      <AlertDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent data-testid="referente-delete-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar Referente</AlertDialogTitle>
            <AlertDialogDescription>Se eliminará «{deleting?.nombre_referente}» del catálogo de forma permanente. Esta acción no se puede deshacer.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="referente-delete-cancel">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-red-600 hover:bg-red-700" data-testid="referente-delete-confirm">Eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <MergeReferentesDialog open={mergeOpen} selected={selected} onClose={() => setMergeOpen(false)} onMerged={() => { setChecked([]); load(); }} />
    </div>
  );
}
