import { Button } from '../../ui/button';
import { Plus, Pencil, ArrowRightLeft, CornerDownRight, Eye, Trash2, FileCheck2 } from 'lucide-react';

const STATUS_STYLE = {
  Certificado: 'bg-emerald-100 text-emerald-700', 'En proceso': 'bg-amber-100 text-amber-700',
  Suspendido: 'bg-red-100 text-red-700', Cerrado: 'bg-slate-200 text-slate-600',
};

export const CompanyAppsPanel = ({ company, canEdit, onAddApp, onEditApp, onViewApp, onMoveApp, onDeleteApp }) => (
  <div className="pl-10 pr-4 py-3 bg-slate-50 border-t border-slate-200 animate-in fade-in slide-in-from-top-1 duration-200" data-testid={`company-apps-panel-${company.empresa_id}`}>
    <div className="flex items-center justify-between mb-2">
      <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5"><CornerDownRight size={13} /> Aplicativos / Integraciones asociadas</p>
      {canEdit && <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => onAddApp(company)} data-testid={`company-add-app-btn-${company.empresa_id}`}><Plus size={13} className="mr-1" />Agregar Aplicativo</Button>}
    </div>
    {company.apps.length === 0 ? <p className="text-xs text-slate-400 py-2">Esta empresa aún no tiene aplicativos.</p> : (
      <table className="w-full text-xs bg-white rounded-md border border-slate-200 overflow-hidden">
        <thead className="bg-slate-100 text-slate-500 text-[11px] uppercase !static !shadow-none">
          <tr>
            <th className="text-left px-3 py-2">Nombre del Aplicativo</th><th className="text-left px-3 py-2">Tipo de Integración</th>
            <th className="text-left px-3 py-2">Modalidad</th><th className="text-left px-3 py-2">Estatus Homologación</th>
            <th className="text-left px-3 py-2">Versión</th><th className="text-left px-3 py-2">Implementador</th><th className="px-3 py-2 w-20" />
          </tr>
        </thead>
        <tbody>
          {company.apps.map(a => (
            <tr key={a.integrator_id} className="border-t border-slate-100 hover:bg-blue-50/40 transition-colors" data-testid={`company-app-row-${a.integrator_id}`}>
              <td className="px-3 py-2 font-semibold text-slate-800" data-testid={`company-app-name-${a.integrator_id}`}>
                <button className="text-left hover:text-brand-blue-600 hover:underline" onClick={() => onViewApp(a)}>{a.app_name || '—'}</button>
                {a.has_certificate && <span className="ml-1.5 inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 font-semibold align-middle" title="Tiene certificado cargado en el histórico" data-testid={`company-app-has-cert-${a.integrator_id}`}><FileCheck2 size={10} />Certificado cargado</span>}
                {a.cert_outdated && <span className="ml-1.5 text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-semibold" data-testid={`company-app-outdated-${a.integrator_id}`}>Cert. desactualizado</span>}
              </td>
              <td className="px-3 py-2"><span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 font-bold text-[10px]">{a.integration_type || '—'}</span></td>
              <td className="px-3 py-2 text-slate-600">{a.integration_modality || '—'}</td>
              <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${STATUS_STYLE[a.integrator_status] || 'bg-slate-100 text-slate-600'}`} data-testid={`company-app-status-${a.integrator_id}`}>{a.integrator_status || '—'}</span>{a.integration_phase && <span className="ml-1 text-[10px] text-slate-400">{a.integration_phase}</span>}</td>
              <td className="px-3 py-2 text-slate-600">{a.cert_version || a.componente_version || '—'}</td>
              <td className="px-3 py-2 text-slate-600">{a.implementador || '—'}</td>
              <td className="px-3 py-2 text-right whitespace-nowrap">
                <button className="text-slate-400 hover:text-emerald-600 p-1" title="Ver ficha completa" onClick={() => onViewApp(a)} data-testid={`company-app-view-${a.integrator_id}`}><Eye size={13} /></button>
                <button className="text-slate-400 hover:text-brand-blue-600 p-1" title="Ver / editar detalle técnico" onClick={() => onEditApp(a)} data-testid={`company-app-edit-${a.integrator_id}`}><Pencil size={13} /></button>
                {canEdit && <button className="text-slate-400 hover:text-amber-600 p-1" title="Mover a otra empresa" onClick={() => onMoveApp(a)} data-testid={`company-app-move-${a.integrator_id}`}><ArrowRightLeft size={13} /></button>}
                {onDeleteApp && <button className="text-slate-400 hover:text-red-600 p-1" title="Eliminar aplicativo" onClick={() => onDeleteApp(a)} data-testid={`company-app-delete-${a.integrator_id}`}><Trash2 size={13} /></button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);
