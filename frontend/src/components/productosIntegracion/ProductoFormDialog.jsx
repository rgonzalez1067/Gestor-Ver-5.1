import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Switch } from '../ui/switch';
import { toast } from 'sonner';
import api from '../../utils/api';

const EMPTY = { codigo: '', nombre: '', descripcion: '', orden_despliegue: '', activo: true };

export const ProductoFormDialog = ({ open, producto, onClose, onSaved }) => {
  const [f, setF] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) setF(producto ? { ...EMPTY, ...producto, orden_despliegue: producto.orden_despliegue ?? '' } : EMPTY);
  }, [open, producto]);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async () => {
    if (!f.codigo.trim() || !f.nombre.trim()) { toast.error('Código y Nombre son obligatorios'); return; }
    const body = { codigo: f.codigo, nombre: f.nombre, descripcion: f.descripcion, activo: f.activo,
      orden_despliegue: f.orden_despliegue === '' ? null : Number(f.orden_despliegue) };
    setSaving(true);
    try {
      if (producto) await api.put(`/productos-integracion/${producto.producto_id}`, body);
      else await api.post('/productos-integracion', body);
      toast.success(producto ? 'Producto actualizado' : 'Producto creado');
      onSaved(); onClose();
    } catch (e) { toast.error(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Error al guardar'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid="producto-form-dialog">
        <DialogHeader><DialogTitle>{producto ? 'Editar Producto' : 'Nuevo Producto para Integración'}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2"><Label>Código *</Label><Input maxLength={30} value={f.codigo} onChange={set('codigo')} placeholder="VPOS_EMV" className="uppercase" data-testid="producto-form-codigo" /></div>
            <div><Label>Orden</Label><Input type="number" value={f.orden_despliegue} onChange={set('orden_despliegue')} data-testid="producto-form-orden" /></div>
          </div>
          <div><Label>Nombre *</Label><Input maxLength={150} value={f.nombre} onChange={set('nombre')} placeholder="Nombre en la Matriz del Integrador" data-testid="producto-form-nombre" /></div>
          <div><Label>Descripción</Label><Textarea rows={3} value={f.descripcion} onChange={set('descripcion')} data-testid="producto-form-descripcion" /></div>
          <label className="flex items-center gap-3"><Switch checked={f.activo} onCheckedChange={(v) => setF({ ...f, activo: v })} data-testid="producto-form-activo" /><span className="text-sm">{f.activo ? 'Activo (visible en la Matriz)' : 'Inactivo'}</span></label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="producto-form-cancel">Cancelar</Button>
          <Button onClick={save} disabled={saving} className="bg-brand-green-600 hover:bg-brand-green-700" data-testid="producto-form-save">{saving ? 'Guardando...' : 'Guardar'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
