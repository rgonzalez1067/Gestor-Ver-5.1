import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { TIPOS_REFERENTE, EMPTY_NUEVO } from './ReferentePicker';
import { toast } from 'sonner';
import api from '../../utils/api';

export const ReferenteFormDialog = ({ open, referente, onClose, onSaved }) => {
  const [form, setForm] = useState(EMPTY_NUEVO);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) setForm(referente ? { nombre_referente: referente.nombre_referente, tipo_referente: referente.tipo_referente, empresa: referente.empresa || '', persona: referente.persona || '' } : { ...EMPTY_NUEVO });
  }, [open, referente]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async () => {
    if (!form.nombre_referente.trim()) { toast.error('El nombre del referente es obligatorio'); return; }
    setSaving(true);
    try {
      if (referente) await api.put(`/referentes/${referente.referente_id}`, form);
      else await api.post('/referentes', form);
      toast.success(referente ? 'Referente actualizado' : 'Referente creado');
      onSaved(); onClose();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid="referente-form-dialog">
        <DialogHeader><DialogTitle>{referente ? 'Editar Referente' : 'Nuevo Referente'}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div><Label>Nombre del Referente *</Label><Input maxLength={150} value={form.nombre_referente} onChange={set('nombre_referente')} data-testid="referente-form-name" /></div>
          <div>
            <Label>Tipo *</Label>
            <div className="flex gap-5 mt-1.5">
              {TIPOS_REFERENTE.map(([k, label]) => (
                <label key={k} className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input type="radio" name="form_tipo_referente" checked={form.tipo_referente === k} onChange={() => setForm({ ...form, tipo_referente: k })} data-testid={`referente-form-tipo-${k}`} />{label}
                </label>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Empresa (Opcional)</Label><Input maxLength={150} value={form.empresa} onChange={set('empresa')} data-testid="referente-form-empresa" /></div>
            <div><Label>Persona (Opcional)</Label><Input maxLength={150} value={form.persona} onChange={set('persona')} data-testid="referente-form-persona" /></div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="referente-form-cancel">Cancelar</Button>
          <Button onClick={save} disabled={saving} className="bg-brand-green-600 hover:bg-brand-green-700" data-testid="referente-form-save">{saving ? 'Guardando...' : 'Guardar'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
