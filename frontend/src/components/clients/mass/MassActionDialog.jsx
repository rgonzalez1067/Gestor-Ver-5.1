import { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Checkbox } from '../../ui/checkbox';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../../utils/api';
import { useClientCatalogs } from '../hierarchy/useClientCatalogs';
import { SearchableSelect } from '../hierarchy/SearchableSelect';

export const MASS_ACTIONS = [
  { id: 'delete', label: 'Eliminar Clientes / Sucursales' },
  { id: 'group_brand', label: 'Asignar Grupo y Marca' },
  { id: 'coord_impl', label: 'Asignar Coordinador e Implementador' },
  { id: 'segment', label: 'Actualizar Segmento' },
  { id: 'ejecutivo', label: 'Reasignar Ejecutivo Propietario' },
  { id: 'categoria', label: 'Actualizar Categoría Comercial' },
  { id: 'integrador', label: 'Asignar Integrador y Aplicativo' },
  { id: 'tipo_servicio', label: 'Actualizar Tipo de Servicio' },
];
const SEGMENTS = ['Pymes', 'Corporativo', 'Emprendedor', 'Mixto'];
const TIPOS = ['VPOS', 'MPOS', 'Payment Gateway', 'Link de Pago'];
const az = (arr) => [...arr].sort((a, b) => (a.name || '').localeCompare(b.name || '', 'es', { sensitivity: 'base' }));
const users = (arr) => az(arr.map(u => ({ id: u.user_id, name: u.full_name })));

const Field = ({ label, children }) => <div><Label className="text-xs mb-1 block">{label}</Label>{children}</div>;

export const MassActionDialog = ({ action, clientIds, onClose, onDone }) => {
  const cat = useClientCatalogs();
  const [p, setP] = useState({});
  const [groups, setGroups] = useState([]);
  const [brands, setBrands] = useState([]);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);
  const [count, setCount] = useState(clientIds.length);
  const set = (patch) => setP(prev => ({ ...prev, ...patch }));

  useEffect(() => {
    setP({}); setResult(null); setCount(clientIds.length);
    if (action === 'group_brand') {
      api.get('/grupos-economicos').then(r => setGroups(r.data || [])).catch(() => {});
      api.get('/marcas').then(r => setBrands(r.data || [])).catch(() => {});
    }
  }, [action]);

  const intgNames = useMemo(() => az([...new Set(cat.integrators.map(i => i.name).filter(Boolean))].map(n => ({ id: n, name: n }))), [cat.integrators]);
  const apps = cat.integrators.filter(i => i.name === p.integrador_name && (i.app_name || '').trim());
  const meta = MASS_ACTIONS.find(a => a.id === action);

  const valid = {
    delete: p.confirm === 'ELIMINAR',
    group_brand: !!(p.grupo_economico_id && p.marca_id),
    coord_impl: (p.apply_coordinator && p.coordinator_user_id) || (p.apply_implementer && p.implementer_user_id),
    segment: !!p.segment, ejecutivo: !!p.ejecutivo_user_id, categoria: !!p.categoria_comercial,
    integrador: !!(p.integrador_id && p.aplicativo), tipo_servicio: (p.tipo_servicio || []).length > 0,
  }[action];

  const run = async () => {
    setSaving(true);
    try {
      const { data } = await api.post('/clients/mass-action', { action, client_ids: clientIds, payload: p });
      setResult(data);
      toast.success(`${data.processed} registro(s) procesado(s)`);
      onDone();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al ejecutar la acción masiva');
    } finally { setSaving(false); }
  };

  const body = () => {
    switch (action) {
      case 'delete': return (
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800 flex gap-2">
            <AlertTriangle size={18} className="shrink-0" />
            <span>Se eliminarán {clientIds.length} registro(s). Los que tengan proyectos en ejecución, cotizaciones aprobadas, órdenes de taller activas o sucursales asociadas se omitirán.</span>
          </div>
          <Field label='Escriba "ELIMINAR" para confirmar'>
            <Input value={p.confirm || ''} onChange={e => set({ confirm: e.target.value })} data-testid="mass-delete-confirm-input" />
          </Field>
        </div>);
      case 'group_brand': return (
        <div className="space-y-3">
          <Field label="Grupo Económico *">
            <SearchableSelect testId="mass-group-select" value={p.grupo_economico_id} emptyLabel="Seleccione un grupo"
              options={az(groups.map(g => ({ id: g.group_id, name: g.name })))} onChange={o => set({ grupo_economico_id: o?.id || '', marca_id: '' })} />
          </Field>
          <Field label="Marca o Nombre Comercial *">
            <SearchableSelect testId="mass-brand-select" disabled={!p.grupo_economico_id} value={p.marca_id}
              emptyLabel={p.grupo_economico_id ? 'Seleccione una marca' : 'Seleccione primero el grupo'}
              options={az(brands.filter(b => b.group_id === p.grupo_economico_id).map(b => ({ id: b.brand_id, name: b.name })))}
              onChange={o => set({ marca_id: o?.id || '' })} />
          </Field>
          <p className="text-[11px] text-slate-500">Se aplica a los RIF (Tienda Principal). Sus sucursales heredan la Marca automáticamente.</p>
        </div>);
      case 'coord_impl': return (
        <div className="space-y-3">
          {[['coordinator', 'Coordinador de Implementación', cat.coordinadores], ['implementer', 'Implementador', cat.implementadores]].map(([k, l, list]) => (
            <div key={k} className="space-y-1.5">
              <label className="flex items-center gap-2 text-xs font-medium"><Checkbox checked={!!p[`apply_${k}`]} onCheckedChange={v => set({ [`apply_${k}`]: !!v })} data-testid={`mass-apply-${k}`} /> Aplicar este campo: {l}</label>
              <SearchableSelect testId={`mass-${k}-select`} disabled={!p[`apply_${k}`]} value={p[`${k}_user_id`]} emptyLabel={`Seleccione ${l.toLowerCase()}`}
                options={users(list)} onChange={o => set({ [`${k}_user_id`]: o?.id || '' })} />
            </div>
          ))}
        </div>);
      case 'segment': return (
        <Field label="Segmento *"><SearchableSelect testId="mass-segment-select" value={p.segment} emptyLabel="Seleccione segmento"
          options={SEGMENTS.map(s => ({ id: s, name: s }))} onChange={o => set({ segment: o?.id || '' })} /></Field>);
      case 'ejecutivo': return (
        <Field label="Ejecutivo Propietario *"><SearchableSelect testId="mass-ejecutivo-select" value={p.ejecutivo_user_id} emptyLabel="Seleccione ejecutivo"
          options={users(cat.ejecutivos)} onChange={o => set({ ejecutivo_user_id: o?.id || '' })} /></Field>);
      case 'categoria': return (
        <Field label="Categoría Comercial *"><SearchableSelect testId="mass-categoria-select" value={p.categoria_comercial} emptyLabel="Seleccione categoría"
          options={az(cat.categories.map(c => ({ id: c.name, name: c.name })))} onChange={o => set({ categoria_comercial: o?.id || '' })} /></Field>);
      case 'integrador': return (
        <div className="space-y-3">
          <Field label="Integrador *"><SearchableSelect testId="mass-integrador-select" value={p.integrador_name} emptyLabel="Seleccione integrador"
            options={intgNames} onChange={o => {
              const docs = cat.integrators.filter(i => i.name === o?.id);
              set({ integrador_name: o?.id || '', integrador_id: docs.length === 1 ? docs[0].integrator_id : '', aplicativo: docs.length === 1 ? (docs[0].app_name || '') : '' });
            }} /></Field>
          <Field label="Aplicativo *"><SearchableSelect testId="mass-aplicativo-select" disabled={!p.integrador_name} value={p.integrador_id}
            emptyLabel={p.integrador_name ? 'Seleccione aplicativo' : 'Seleccione primero el integrador'}
            options={apps.map(a => ({ id: a.integrator_id, name: a.app_name }))} onChange={o => set({ integrador_id: o?.id || '', aplicativo: o?.name || '' })} /></Field>
        </div>);
      case 'tipo_servicio': return (
        <Field label="Tipo de Servicio *">
          <div className="flex flex-wrap gap-1.5" data-testid="mass-tipo-servicio">
            {TIPOS.map(t => {
              const on = (p.tipo_servicio || []).includes(t);
              return <button key={t} type="button" data-testid={`mass-tipo-${t.replace(/\s+/g, '-')}`}
                onClick={() => set({ tipo_servicio: on ? p.tipo_servicio.filter(x => x !== t) : [...(p.tipo_servicio || []), t] })}
                className={`px-2.5 py-1 rounded-full text-xs border ${on ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-300'}`}>{t}</button>;
            })}
          </div>
        </Field>);
      default: return null;
    }
  };

  return (
    <Dialog open={!!action} onOpenChange={o => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid={`mass-dialog-${action}`}>
        <DialogHeader><DialogTitle>{meta?.label} <span className="text-sm font-normal text-slate-500">({count} seleccionados)</span></DialogTitle></DialogHeader>
        {result ? (
          <div className="space-y-3" data-testid="mass-result">
            <p className="text-sm text-emerald-700 font-medium">Procesados: <span data-testid="mass-result-processed">{result.processed}</span></p>
            {result.skipped?.length > 0 && (
              <div className="border border-amber-200 bg-amber-50 rounded-lg p-3 max-h-60 overflow-y-auto" data-testid="mass-result-skipped">
                <p className="text-xs font-semibold text-amber-800 mb-1.5">Omitidos ({result.skipped.length}):</p>
                {result.skipped.map(s => <p key={s.client_id} className="text-xs text-amber-900" data-testid={`mass-skipped-${s.client_id}`}>• {s.label}: {s.reasons.join(', ')}</p>)}
              </div>
            )}
            <div className="flex justify-end"><Button onClick={onClose} data-testid="mass-result-close">Cerrar</Button></div>
          </div>
        ) : (
          <>
            {body()}
            <div className="flex justify-end gap-2 pt-3 border-t">
              <Button variant="outline" onClick={onClose} data-testid="mass-cancel-btn">Cancelar</Button>
              <Button disabled={!valid || saving} onClick={run} data-testid="mass-apply-btn"
                className={action === 'delete' ? 'bg-red-600 hover:bg-red-700' : 'bg-indigo-600 hover:bg-indigo-700'}>
                {saving ? 'Procesando...' : action === 'delete' ? 'Eliminar' : 'Aplicar'}
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
