import { useState } from 'react';
import { Button } from '../ui/button';
import { Edit2, Phone, Mail, Wrench } from 'lucide-react';
import { IntegrationTechniciansReel, technicianError } from './IntegrationTechniciansReel';
import api from '../../utils/api';
import { toast } from 'sonner';

export const ProjectTechniciansCard = ({ project, canEdit, onSaved }) => {
  const [editing, setEditing] = useState(false);
  const [techs, setTechs] = useState([]);
  const list = project.integration_technicians || [];

  const start = () => { setTechs(list.map(t => ({ ...t }))); setEditing(true); };
  const save = async () => {
    const err = technicianError(techs);
    if (err) { toast.error(err); return; }
    try {
      await api.put(`/projects/${project.project_id}/implementation-fields`, { integration_technicians: techs.filter(t => t.name.trim()) });
      toast.success('Técnicos responsables actualizados'); setEditing(false); onSaved();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al guardar técnicos'); }
  };

  if (editing) return (
    <div className="space-y-2 pb-2 border-b border-slate-100" data-testid="project-techs-editor">
      <IntegrationTechniciansReel value={techs} onChange={setTechs} integratorId={project.integrator_id} testPrefix="pd-tech" />
      <div className="flex gap-1">
        <Button size="sm" className="h-6 text-[10px]" onClick={save} data-testid="project-techs-save-btn">Guardar</Button>
        <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => setEditing(false)}>Cancelar</Button>
      </div>
    </div>
  );
  return (
    <div className="pb-2 border-b border-slate-100" data-testid="project-techs-view">
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-slate-500 flex items-center gap-1"><Wrench size={11} /> Técnicos Responsables ({list.length})</p>
        {canEdit && <button onClick={start} className="text-slate-400 hover:text-blue-500" data-testid="edit-project-techs-btn"><Edit2 size={12} /></button>}
      </div>
      {list.length === 0 ? <p className="text-xs text-slate-400">Sin técnicos asignados</p> : (
        <ul className="space-y-1.5">
          {list.map((t, i) => (
            <li key={t.tech_id || i} className="text-xs" data-testid={`project-tech-${i}`}>
              <span className="font-semibold text-slate-700">{t.name}</span>{t.role && <span className="ml-1 px-1.5 py-0.5 rounded bg-cyan-50 text-cyan-700 text-[10px]">{t.role}</span>}
              <div className="flex flex-wrap gap-x-3 text-slate-500 mt-0.5">
                {t.phone && <span className="inline-flex items-center gap-1"><Phone size={10} />{t.phone}</span>}
                {t.email && <span className="inline-flex items-center gap-1"><Mail size={10} />{t.email}</span>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
