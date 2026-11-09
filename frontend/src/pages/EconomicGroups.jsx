import { useState, useEffect, Fragment } from 'react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Plus, Pencil, Trash2, X, Search, Building2, FileDown, UserPlus, ChevronRight, ChevronDown, GitBranch } from 'lucide-react';
import { CharacteristicsEditor } from '../components/clients/hierarchy/CharacteristicsEditor';
import { CorporateContactsEditor } from '../components/clients/hierarchy/CorporateContactsEditor';
import { GroupTree } from '../components/clients/hierarchy/HierarchyTree';
import api from '../utils/api';
import { toast } from 'sonner';
import { usePermission } from '../hooks/usePermission';

const emptyRepresentante = () => ({ nombre: '', cedula: '', cargo: '', telefono: '', email: '' });
const emptyGroup = () => ({ name: '', description: '', representantes: [], contacts: [], characteristics: {} });

export default function EconomicGroups() {
  const { canEdit } = usePermission('grupos_economicos');
  const editable = canEdit;

  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(emptyGroup());
  const [expanded, setExpanded] = useState({});
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const fetchGroups = async () => {
    setLoading(true);
    try {
      const res = await api.get('/grupos-economicos', { params: search ? { search } : {} });
      setGroups(res.data || []);
    } catch {
      toast.error('Error al cargar los grupos económicos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchGroups(); /* eslint-disable-next-line */ }, []);
  useEffect(() => { const t = setTimeout(fetchGroups, 300); return () => clearTimeout(t); /* eslint-disable-next-line */ }, [search]);

  const openCreate = () => {
    setEditingId(null); setForm(emptyGroup()); setDialogOpen(true);
  };

  const openEdit = async (groupId) => {
    try {
      const res = await api.get(`/grupos-economicos/${groupId}`);
      const g = res.data;
      setEditingId(groupId);
      setForm({
        name: g.name || '',
        description: g.description || '',
        representantes: (g.representantes || []).map(r => ({ ...emptyRepresentante(), ...r })),
        contacts: (g.contacts || []).map(c => ({ contact_id: '', full_name: '', phone: '', email: '', role: 'Administrativo', ...c, purposes: c.purposes || [] })),
        characteristics: g.characteristics || {},
      });
      setDialogOpen(true);
    } catch {
      toast.error('No se pudo abrir el grupo');
    }
  };

  const setField = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  // Representantes
  const addRepresentante = () => setForm(p => ({ ...p, representantes: [...p.representantes, emptyRepresentante()] }));
  const updateRepresentante = (idx, field, value) => setForm(p => {
    const r = [...p.representantes]; r[idx] = { ...r[idx], [field]: value }; return { ...p, representantes: r };
  });
  const removeRepresentante = (idx) => setForm(p => ({ ...p, representantes: p.representantes.filter((_, i) => i !== idx) }));

  const save = async () => {
    if (!form.name.trim()) { toast.error('El nombre del grupo es obligatorio'); return; }
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description || '',
        representantes: form.representantes.filter(r => r.nombre.trim()),
        contacts: form.contacts.filter(c => c.full_name.trim() || c.email.trim()),
        characteristics: form.characteristics || {},
      };
      if (editingId) {
        await api.put(`/grupos-economicos/${editingId}`, payload);
        toast.success('Grupo actualizado');
      } else {
        await api.post('/grupos-economicos', payload);
        toast.success('Grupo creado');
      }
      setDialogOpen(false);
      fetchGroups();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const doDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/grupos-economicos/${deleteTarget.group_id}`);
      toast.success('Grupo eliminado');
      setDeleteTarget(null);
      fetchGroups();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al eliminar');
    }
  };

  const downloadPdf = async (group) => {
    try {
      const res = await api.get(`/grupos-economicos/${group.group_id}/export-pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url; a.download = `Grupo_${group.name}.pdf`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    } catch {
      toast.error('No se pudo generar el PDF');
    }
  };

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-auto p-8" data-testid="economic-groups-page">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-2">
              <Building2 className="text-indigo-600" size={28} /> Grupo Económico
            </h1>
            <p className="text-slate-500 mt-1">Grupos corporativos y sus Marcas. Haga clic en un grupo para desplegar Marcas → RIFs → Sucursales.</p>
          </div>
          {editable && (
            <Button onClick={openCreate} className="bg-indigo-600 hover:bg-indigo-700" data-testid="create-group-btn">
              <Plus size={16} className="mr-1.5" /> Nuevo Grupo
            </Button>
          )}
        </div>

        <div className="relative mb-4 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input placeholder="Buscar grupo económico..." value={search} onChange={e => setSearch(e.target.value)}
            className="pl-9" data-testid="group-search-input" />
        </div>

        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-3">Nombre del Grupo</th>
                <th className="text-left px-4 py-3">Descripción</th>
                <th className="text-center px-4 py-3">Marcas</th>
                <th className="text-center px-4 py-3">RIFs Asociados</th>
                <th className="text-center px-4 py-3">Contactos</th>
                <th className="text-right px-4 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-8 text-slate-400">Cargando...</td></tr>
              ) : groups.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-8 text-slate-400">No hay grupos económicos.</td></tr>
              ) : groups.map(g => (
                <Fragment key={g.group_id}>
                <tr className="border-t hover:bg-slate-50" data-testid={`group-row-${g.group_id}`}>
                  <td className="px-4 py-3 font-medium text-slate-800">
                    <button type="button" onClick={() => setExpanded(p => ({ ...p, [g.group_id]: !p[g.group_id] }))} className="flex items-center gap-2 hover:text-indigo-700" data-testid={`group-expand-${g.group_id}`}>
                      {expanded[g.group_id] ? <ChevronDown size={15} /> : <ChevronRight size={15} />}{g.name}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-slate-500 max-w-xs truncate">{g.description || '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 font-semibold" data-testid={`group-brand-count-${g.group_id}`}>{g.brands_count ?? 0}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-semibold" data-testid={`group-rif-count-${g.group_id}`}>{g.rif_count}</span>
                  </td>
                  <td className="px-4 py-3 text-center text-slate-600">{g.contacts_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => downloadPdf(g)} title="Descargar PDF" data-testid={`group-pdf-${g.group_id}`}>
                        <FileDown size={15} className="text-slate-500" />
                      </Button>
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => openEdit(g.group_id)} title="Editar" data-testid={`group-edit-${g.group_id}`}>
                        <Pencil size={15} className="text-slate-500" />
                      </Button>
                      {editable && (
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => setDeleteTarget(g)} title="Eliminar" data-testid={`group-delete-${g.group_id}`}>
                          <Trash2 size={15} className="text-red-500" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
                {expanded[g.group_id] && (
                  <tr className="bg-slate-50/60" data-testid={`group-tree-row-${g.group_id}`}><td colSpan={6} className="px-6 py-2"><GroupTree groupId={g.group_id} /></td></tr>
                )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {/* Edit/Create Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" data-testid="group-dialog">
            <DialogHeader>
              <DialogTitle>{editingId ? 'Editar Grupo Económico' : 'Nuevo Grupo Económico'}</DialogTitle>
            </DialogHeader>

            <div className="space-y-6">
              {/* A. Datos principales */}
              <div className="grid grid-cols-1 gap-3">
                <div>
                  <Label className="text-xs">Nombre del Grupo Económico *</Label>
                  <Input value={form.name} onChange={e => setField('name', e.target.value)}
                    disabled={!editable} data-testid="group-name-input" />
                </div>
                <div>
                  <Label className="text-xs">Breve Descripción</Label>
                  <Textarea value={form.description} onChange={e => setField('description', e.target.value)}
                    rows={2} disabled={!editable} data-testid="group-description-input" />
                </div>
              </div>

              {/* Representantes Legales */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5"><UserPlus size={15} /> Representantes Legales</h3>
                  {editable && <Button size="sm" variant="outline" onClick={addRepresentante} data-testid="add-representante-btn"><Plus size={14} className="mr-1" /> Agregar</Button>}
                </div>
                {form.representantes.length === 0 && <p className="text-xs text-slate-400">Sin representantes (opcional).</p>}
                <div className="space-y-2">
                  {form.representantes.map((r, idx) => (
                    <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-slate-50 p-2 rounded" data-testid={`representante-${idx}`}>
                      <Input className="col-span-3" placeholder="Nombre" value={r.nombre} onChange={e => updateRepresentante(idx, 'nombre', e.target.value)} disabled={!editable} data-testid={`representante-nombre-${idx}`} />
                      <Input className="col-span-2" placeholder="Cédula" value={r.cedula} onChange={e => updateRepresentante(idx, 'cedula', e.target.value)} disabled={!editable} />
                      <Input className="col-span-2" placeholder="Cargo" value={r.cargo} onChange={e => updateRepresentante(idx, 'cargo', e.target.value)} disabled={!editable} />
                      <Input className="col-span-2" placeholder="Teléfono" value={r.telefono} onChange={e => updateRepresentante(idx, 'telefono', e.target.value)} disabled={!editable} />
                      <Input className="col-span-2" placeholder="Email" value={r.email} onChange={e => updateRepresentante(idx, 'email', e.target.value)} disabled={!editable} />
                      {editable && <Button size="sm" variant="ghost" className="col-span-1 h-8 w-8 p-0 text-red-500" onClick={() => removeRepresentante(idx)}><X size={15} /></Button>}
                    </div>
                  ))}
                </div>
              </div>

              <CharacteristicsEditor value={form.characteristics} onChange={v => setField('characteristics', v)} disabled={!editable} testPrefix="group-char" />

              <CorporateContactsEditor contacts={form.contacts} onChange={v => setField('contacts', v)} editable={editable} title="Contactos Corporativos" />

              {editingId && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5 mb-2"><GitBranch size={15} /> Marcas, RIFs y Sucursales</h3>
                  <div className="border border-slate-200 rounded-lg p-2" data-testid="group-dialog-tree"><GroupTree groupId={editingId} /></div>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cerrar</Button>
              {editable && <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-group-btn">{saving ? 'Guardando...' : 'Guardar'}</Button>}
            </div>
          </DialogContent>
        </Dialog>

        <AlertDialog open={!!deleteTarget} onOpenChange={o => !o && setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Eliminar Grupo Económico</AlertDialogTitle>
              <AlertDialogDescription>
                ¿Eliminar "{deleteTarget?.name}"? Los clientes vinculados se desvincularán (no se borran).
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={doDelete} className="bg-red-600 hover:bg-red-700" data-testid="confirm-delete-group">Eliminar</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </main>
    </div>
  );
}
