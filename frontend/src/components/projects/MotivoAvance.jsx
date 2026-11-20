import { useState } from 'react';
import { toast } from 'sonner';
import api from '../../utils/api';
import { Building2, Landmark, Wrench, CircleSlash } from 'lucide-react';

export const MOTIVOS_AVANCE = [
  { key: 'CLIENTE', label: 'Cliente', icon: Building2, cls: 'bg-red-500', on: 'bg-red-500 text-white border-red-600 shadow-sm', off: 'hover:bg-red-50 hover:text-red-600 hover:border-red-200', hint: 'Demoras, recaudos, adecuaciones o disponibilidad del comercio' },
  { key: 'BANCO', label: 'Banco', icon: Landmark, cls: 'bg-blue-500', on: 'bg-blue-600 text-white border-blue-700 shadow-sm', off: 'hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200', hint: 'Aprobaciones, afiliaciones, credenciales o parámetros de la entidad financiera' },
  { key: 'IMPLE', label: 'Imple', icon: Wrench, cls: 'bg-yellow-400', on: 'bg-yellow-400 text-black border-yellow-500 shadow-sm', off: 'hover:bg-yellow-50 hover:text-yellow-800 hover:border-yellow-300', hint: 'Gestión técnica, configuración, agenda o ejecución de Implementación Mega Soft' },
];
export const motivoOf = (p) => (p?.motivo_avance || '').toUpperCase() || null;

// Botones de color Cliente / Banco / Imple; pulsar el activo lo deja sin motivo.
const MotivoButtons = ({ project, canEdit, onChanged, compact, testPrefix }) => {
  const [value, setValue] = useState(motivoOf(project));
  const [busy, setBusy] = useState(false);
  const pick = async (key) => {
    if (!canEdit || busy) return;
    const next = key === value ? null : key;
    setBusy(true);
    try {
      await api.put(`/projects/${project.project_id}/motivo-avance`, { motivo: next });
      setValue(next);
      toast.success(next ? 'Responsable del Avance actualizado' : 'Responsable del Avance retirado');
      onChanged?.(next);
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo actualizar el responsable'); }
    finally { setBusy(false); }
  };
  return (
    <div className="inline-flex gap-1" role="radiogroup" data-testid={`${testPrefix}-group`}>
      {MOTIVOS_AVANCE.map(({ key, label, icon: Icon, hint, on, off }) => (
        <button key={key} type="button" role="radio" aria-checked={value === key} disabled={busy}
          title={canEdit ? hint : `${hint} (solo lectura)`}
          onClick={() => pick(key)} data-testid={`${testPrefix}-${key}`} data-active={value === key ? 'true' : 'false'}
          className={`inline-flex items-center gap-1 rounded-md border font-medium transition-[background-color,color,transform] duration-150 ${compact ? 'px-1.5 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs'} ${value === key ? on : `bg-white text-slate-500 border-slate-200 ${canEdit ? off : ''}`} ${canEdit ? 'active:scale-95' : 'cursor-default opacity-90'}`}>
          <Icon size={compact ? 10 : 12} />{label}
        </button>
      ))}
    </div>
  );
};

export const MotivoAvanceGridButtons = ({ project, canEdit, onChanged }) => (
  <MotivoButtons key={project.motivo_avance || 'NONE'} project={project} canEdit={canEdit} onChanged={onChanged} compact
    testPrefix={`grid-motivo-${project.project_id}`} />
);

// Selector "Motivo del Avance" en la ficha del proyecto.
export const MotivoAvanceSelector = ({ project, canEdit, onChanged }) => (
  <div data-testid="motivo-avance-section">
    <p className="text-xs text-slate-500 mb-1">Responsable del Avance</p>
    <MotivoButtons project={project} canEdit={canEdit} onChanged={onChanged} testPrefix="motivo-avance" />
    {!canEdit && <p className="text-[10px] text-slate-400 mt-0.5">Solo el implementador del proyecto o un administrador puede cambiarlo.</p>}
  </div>
);

// Desglose de responsabilidad para una categoría de avance (usado en tooltips de KPIs).
export const MotivoBreakdown = ({ projects, testId }) => {
  const total = projects.length;
  if (!total) return null;
  const rows = [...MOTIVOS_AVANCE, { key: 'NONE', label: 'Sin responsable', cls: 'bg-slate-400' }];
  return (
    <div className="pl-4 mt-0.5 space-y-0.5" data-testid={testId}>
      {rows.map(m => {
        const n = projects.filter(p => (motivoOf(p) || 'NONE') === m.key).length;
        if (m.key === 'NONE' && !n) return null;
        return (
          <div key={m.key} className="flex items-center justify-between gap-3 text-[11px] text-slate-300">
            <span className="flex items-center gap-1"><span className={`w-1.5 h-1.5 rounded-full ${m.cls}`} />{m.label}</span>
            <span className="tabular-nums" data-testid={`${testId}-${m.key}`}>{n} ({((n / total) * 100).toFixed(1)}%)</span>
          </div>
        );
      })}
    </div>
  );
};

// Barra de filtro rápido por Motivo del Avance (con contadores); clic de nuevo quita el filtro.
export const MotivoFilterBar = ({ projects, value, onChange }) => {
  const rows = [...MOTIVOS_AVANCE, { key: 'NONE', label: 'Sin responsable', icon: CircleSlash, on: 'bg-slate-600 text-white border-slate-700 shadow-sm', off: 'hover:bg-slate-100 hover:border-slate-300' }];
  const count = (k) => projects.filter(p => (motivoOf(p) || 'NONE') === k).length;
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2" data-testid="motivo-filter-bar">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Responsable del Avance:</span>
      {rows.map(({ key, label, icon: Icon, on, off }) => (
        <button key={key} type="button" onClick={() => onChange(value === key ? 'all' : key)}
          data-testid={`motivo-filter-${key}`} data-active={value === key ? 'true' : 'false'}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-[background-color,color,transform] duration-150 active:scale-95 ${value === key ? on : `bg-white text-slate-600 border-slate-200 ${off}`}`}>
          <Icon size={12} />{label}
          <span className={`rounded-full px-1.5 tabular-nums ${value === key ? 'bg-black/15' : 'bg-slate-100'}`} data-testid={`motivo-filter-count-${key}`}>{count(key)}</span>
        </button>
      ))}
      {value !== 'all' && (
        <button type="button" onClick={() => onChange('all')} className="text-xs text-slate-500 underline hover:text-slate-800" data-testid="motivo-filter-clear">Quitar filtro</button>
      )}
    </div>
  );
};
