import { useState } from 'react';
import { toast } from 'sonner';
import api from '../../utils/api';
import { Building2, Landmark, Wrench } from 'lucide-react';

export const MOTIVOS_AVANCE = [
  { key: 'CLIENTE', label: 'Cliente', icon: Building2, cls: 'bg-orange-500', hint: 'Demoras, recaudos, adecuaciones o disponibilidad del comercio' },
  { key: 'BANCO', label: 'Banco', icon: Landmark, cls: 'bg-sky-500', hint: 'Aprobaciones, afiliaciones, credenciales o parámetros de la entidad financiera' },
  { key: 'IMPLE', label: 'Imple', icon: Wrench, cls: 'bg-violet-500', hint: 'Gestión técnica, configuración, agenda o ejecución de Implementación Mega Soft' },
];
export const motivoOf = (p) => (p?.motivo_avance || 'IMPLE').toUpperCase();

// Selector "Motivo del Avance" (Cliente / Banco / Imple) en la ficha del proyecto.
export const MotivoAvanceSelector = ({ project, canEdit, onChanged }) => {
  const [value, setValue] = useState(motivoOf(project));
  const [busy, setBusy] = useState(false);
  const pick = async (key) => {
    if (!canEdit || busy || key === value) return;
    setBusy(true);
    try {
      await api.put(`/projects/${project.project_id}/motivo-avance`, { motivo: key });
      setValue(key);
      toast.success('Motivo del Avance actualizado y registrado en la Bitácora');
      onChanged?.();
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo actualizar el motivo'); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid="motivo-avance-section">
      <p className="text-xs text-slate-500 mb-1">Motivo del Avance</p>
      <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5" role="radiogroup">
        {MOTIVOS_AVANCE.map(({ key, label, icon: Icon, hint }) => (
          <button key={key} type="button" role="radio" aria-checked={value === key} title={hint} disabled={!canEdit || busy}
            onClick={() => pick(key)} data-testid={`motivo-avance-${key}`}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${value === key ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200' : 'text-slate-500'} ${canEdit ? 'hover:text-slate-800' : 'cursor-default'}`}>
            <Icon size={12} />{label}
          </button>
        ))}
      </div>
      {!canEdit && <p className="text-[10px] text-slate-400 mt-0.5">Solo el equipo de Implementación o un administrador puede cambiarlo.</p>}
    </div>
  );
};

// Desglose de responsabilidad para una categoría de avance (usado en tooltips de KPIs).
export const MotivoBreakdown = ({ projects, testId }) => {
  const total = projects.length;
  if (!total) return null;
  return (
    <div className="pl-4 mt-0.5 space-y-0.5" data-testid={testId}>
      {MOTIVOS_AVANCE.map(m => {
        const n = projects.filter(p => motivoOf(p) === m.key).length;
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
