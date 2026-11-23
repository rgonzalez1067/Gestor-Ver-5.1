import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../ui/dialog';
import { Button } from '../../ui/button';
import { AlertTriangle, Trash2, ExternalLink } from 'lucide-react';
import api from '../../../utils/api';
import { toast } from 'sonner';

const RefList = ({ title, items, render, testId }) => !items?.length ? null : (
  <div data-testid={testId}>
    <p className="text-xs font-semibold text-slate-700 mb-1">{title} ({items.length})</p>
    <ul className="max-h-40 overflow-y-auto border rounded-md divide-y text-xs">{items.map(render)}</ul>
  </div>
);

export const DeleteAppDialog = ({ app, onClose, onDeleted }) => {
  const [refs, setRefs] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setRefs(null);
    if (app) api.get(`/integrators/${app.integrator_id}/references`).then((r) => setRefs(r.data)).catch(() => setRefs({ quotes: [], projects: [], certificates: 0 }));
  }, [app]);
  const blocked = refs && (refs.quotes.length || refs.projects.length || refs.certificates);

  const remove = async () => {
    setBusy(true);
    try { const { data } = await api.delete(`/integrators/${app.integrator_id}/safe`); toast.success(data.message); onClose(); onDeleted(); }
    catch (e) { const d = e.response?.data?.detail; toast.error(typeof d === 'string' ? d : d?.message || 'No se pudo eliminar'); if (d?.quotes) setRefs(d); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={!!app} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid="delete-app-dialog">
        <DialogHeader><DialogTitle className="text-base">Eliminar aplicativo «{app?.app_name || '—'}»</DialogTitle></DialogHeader>
        {!refs ? <p className="text-sm text-slate-400">Verificando referencias...</p> : blocked ? (
          <div className="space-y-3">
            <p className="text-xs rounded-md bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 flex gap-2" data-testid="delete-app-blocked">
              <AlertTriangle size={14} className="shrink-0 mt-0.5" />No se puede eliminar: está referido por los registros siguientes. Actualice esas cotizaciones/proyectos con el aplicativo correcto y vuelva a intentarlo.</p>
            <RefList title="Cotizaciones" items={refs.quotes} testId="delete-app-quotes" render={(q) => (
              <li key={q.quote_id} className="px-3 py-1.5 flex items-center gap-2"><a href={`/quotes?search=${encodeURIComponent(q.quote_number || '')}`} target="_blank" rel="noreferrer" className="font-semibold text-brand-blue-600 hover:underline inline-flex items-center gap-1">{q.quote_number}<ExternalLink size={10} /></a><span className="text-slate-500 truncate">{q.client_name}</span><span className="ml-auto text-[10px] text-slate-400">{q.status}</span></li>
            )} />
            <RefList title="Proyectos" items={refs.projects} testId="delete-app-projects" render={(p) => (
              <li key={p.project_id} className="px-3 py-1.5 flex items-center gap-2"><a href={`/projects/${p.project_id}`} target="_blank" rel="noreferrer" className="font-semibold text-brand-blue-600 hover:underline inline-flex items-center gap-1">{p.project_number || p.project_id}<ExternalLink size={10} /></a><span className="text-slate-500 truncate">{p.client_name}</span><span className="ml-auto text-[10px] text-slate-400">{p.status}</span></li>
            )} />
            {refs.certificates > 0 && <p className="text-xs text-slate-600" data-testid="delete-app-certs">Tiene {refs.certificates} certificado(s) en el histórico (anúlelos primero si es un duplicado).</p>}
          </div>
        ) : <p className="text-sm text-slate-600" data-testid="delete-app-ok">El aplicativo no tiene cotizaciones, proyectos ni certificados asociados. Esta acción no se puede deshacer.</p>}
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button disabled={!refs || !!blocked || busy} onClick={remove} className="bg-red-600 hover:bg-red-700" data-testid="delete-app-confirm-btn"><Trash2 size={14} className="mr-1" />Eliminar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
