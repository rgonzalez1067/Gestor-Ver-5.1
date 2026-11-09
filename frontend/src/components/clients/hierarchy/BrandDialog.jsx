import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Textarea } from '../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { toast } from 'sonner';
import api from '../../../utils/api';
import { CharacteristicsEditor } from './CharacteristicsEditor';
import { CorporateContactsEditor } from './CorporateContactsEditor';
import { InheritedContactsPanel } from './InheritedContactsPanel';
import { RifList } from './HierarchyTree';

const NONE = '_none_';
const empty = (groupId) => ({ name: '', group_id: groupId || '', description: '', characteristics: {}, contacts: [] });
const groupInherited = (g) => {
  const values = g?.characteristics || {};
  return { values, sources: Object.fromEntries(Object.keys(values).map(k => [k, { level: 'grupo' }])) };
};

// Alta/edición de Marca. `fixedGroupId` bloquea el grupo (alta rápida desde la ficha de cliente).
export const BrandDialog = ({ open, onClose, brandId, fixedGroupId, editable = true, onSaved }) => {
  const [form, setForm] = useState(empty(fixedGroupId));
  const [groups, setGroups] = useState([]);
  const [group, setGroup] = useState(null);
  const [saving, setSaving] = useState(false);
  const set = (patch) => setForm(p => ({ ...p, ...patch }));

  useEffect(() => {
    if (!open) return;
    api.get('/grupos-economicos').then(r => setGroups(r.data || [])).catch(() => setGroups([]));
    if (brandId) {
      api.get(`/marcas/${brandId}`).then(r => setForm({ ...empty(), ...r.data, group_id: r.data.group_id || '', contacts: r.data.contacts || [], characteristics: r.data.characteristics || {} }))
        .catch(() => toast.error('No se pudo abrir la marca'));
    } else setForm(empty(fixedGroupId));
  }, [open, brandId, fixedGroupId]);

  useEffect(() => {
    if (!form.group_id) { setGroup(null); return; }
    api.get(`/grupos-economicos/${form.group_id}`).then(r => setGroup(r.data)).catch(() => setGroup(null));
  }, [form.group_id]);

  const save = async () => {
    if (!form.name.trim()) { toast.error('El nombre de la Marca es obligatorio'); return; }
    setSaving(true);
    try {
      const payload = { ...form, group_id: form.group_id || null };
      const res = brandId ? await api.put(`/marcas/${brandId}`, payload) : await api.post('/marcas', payload);
      toast.success(brandId ? 'Marca actualizada' : 'Marca creada');
      onSaved?.(res.data);
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al guardar la marca');
    } finally { setSaving(false); }
  };

  const groupContacts = (group?.contacts || []).filter(c => (c.email || '').trim())
    .map(c => ({ ...c, scope: 'grupo', level_name: group?.name, effective: true }));
  const ownHas = form.contacts.some(c => (c.email || '').trim());

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" data-testid="brand-dialog">
        <DialogHeader><DialogTitle>{brandId ? 'Editar Marca o Nombre Comercial' : 'Nueva Marca o Nombre Comercial'}</DialogTitle></DialogHeader>
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Nombre de la Marca / Fantasía *</Label>
              <Input value={form.name} onChange={e => set({ name: e.target.value })} disabled={!editable} data-testid="brand-name-input" />
            </div>
            <div>
              <Label className="text-xs">Grupo Económico</Label>
              <Select value={form.group_id || NONE} onValueChange={v => set({ group_id: v === NONE ? '' : v })} disabled={!editable || !!fixedGroupId}>
                <SelectTrigger className="h-9" data-testid="brand-group-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>— Sin grupo —</SelectItem>
                  {groups.map(g => <SelectItem key={g.group_id} value={g.group_id}>{g.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-2">
              <Label className="text-xs">Breve Descripción</Label>
              <Textarea rows={2} value={form.description || ''} onChange={e => set({ description: e.target.value })} disabled={!editable} data-testid="brand-description-input" />
            </div>
          </div>
          <CharacteristicsEditor value={form.characteristics} onChange={v => set({ characteristics: v })}
            inherited={groupInherited(group)} disabled={!editable} testPrefix="brand-char" />
          <div>
            <InheritedContactsPanel contacts={groupContacts} ownHasContacts={ownHas} testId="brand-inherited-contacts" />
            <CorporateContactsEditor contacts={form.contacts} onChange={v => set({ contacts: v })} editable={editable}
              title="Contactos de la Marca" testPrefix="brand-contact" addTestId="add-brand-contact-btn" />
          </div>
          {brandId && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">RIFs y Sucursales de la Marca</h3>
              <div className="border border-slate-200 rounded-lg p-2"><RifList brandId={brandId} /></div>
            </div>
          )}
        </div>
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose} data-testid="brand-dialog-close">Cerrar</Button>
          {editable && <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-brand-btn">{saving ? 'Guardando...' : 'Guardar'}</Button>}
        </div>
      </DialogContent>
    </Dialog>
  );
};
