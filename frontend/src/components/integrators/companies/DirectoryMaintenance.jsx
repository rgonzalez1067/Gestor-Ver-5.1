import { useRef, useState } from 'react';
import { Button } from '../../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Trash2, FileStack, Upload } from 'lucide-react';
import api from '../../../utils/api';
import { toast } from 'sonner';

const ResultDialog = ({ result, onClose }) => (
  <Dialog open={!!result} onOpenChange={(o) => !o && onClose()}>
    <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="maintenance-result-dialog">
      <DialogHeader><DialogTitle className="text-base">{result?.title}</DialogTitle></DialogHeader>
      <p className="text-sm text-emerald-700 font-semibold" data-testid="maintenance-result-ok">{result?.ok}</p>
      {result?.okItems?.length > 0 && <ul className="text-xs border rounded-md divide-y max-h-48 overflow-y-auto">{result.okItems.map((t, i) => <li key={i} className="px-3 py-1.5">{t}</li>)}</ul>}
      {result?.bad?.length > 0 && (<>
        <p className="text-sm text-amber-700 font-semibold mt-2">Pendientes ({result.bad.length})</p>
        <ul className="text-xs border border-amber-200 rounded-md divide-y max-h-56 overflow-y-auto" data-testid="maintenance-result-pending">{result.bad.map((t, i) => <li key={i} className="px-3 py-1.5">{t}</li>)}</ul>
      </>)}
    </DialogContent>
  </Dialog>
);

export const DirectoryMaintenance = ({ emptyCount, canDelete, canManageCerts, onDone }) => {
  const [busy, setBusy] = useState('');
  const [result, setResult] = useState(null);
  const zipRef = useRef(null);

  const run = async (key, fn) => {
    setBusy(key);
    try { await fn(); onDone(); } catch (e) { toast.error(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Error en la operación'); }
    finally { setBusy(''); }
  };
  const purge = () => {
    if (!window.confirm(`¿Eliminar ${emptyCount} Empresa(s) Integradora(s) sin aplicativos? Esta acción no se puede deshacer.`)) return;
    run('purge', async () => { const { data } = await api.post('/integrator-companies/purge-empty'); toast.success(`${data.deleted} empresa(s) eliminada(s)`); });
  };
  const rebuild = () => run('rebuild', async () => {
    const { data } = await api.post('/integrators/certificates/rebuild-legacy');
    setResult({ title: 'Reconstrucción de certificados', ok: `${data.created} certificado(s) reconstruido(s) en el histórico`,
      okItems: data.items.map((i) => `${i.name} · ${i.app_name}`), bad: data.skipped.map((s) => `${s.name} · ${s.app_name} — ${s.reason}`) });
  });
  const upload = (e) => {
    const f = e.target.files?.[0]; e.target.value = '';
    if (!f) return;
    run('zip', async () => {
      const fd = new FormData(); fd.append('file', f);
      const { data } = await api.post('/integrators/certificates/bulk-upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setResult({ title: 'Carga de certificados en lote', ok: `${data.matched.length} certificado(s) asociado(s)`,
        okItems: data.matched.map((m) => `${m.filename} → ${m.name} · ${m.app_name}`),
        bad: data.unmatched.map((u) => `${u.filename} — ${u.reason} (cárguelo manualmente en Ficha del Aplicativo → Certificados)`) });
    });
  };

  if (!canDelete && !canManageCerts) return null;
  return (
    <div className="flex items-center gap-2 flex-wrap" data-testid="directory-maintenance">
      {canDelete && <Button size="sm" variant="outline" className="h-8 text-xs bg-transparent text-white border-slate-500 hover:bg-slate-800 hover:text-white" disabled={!emptyCount || !!busy} onClick={purge} data-testid="purge-empty-companies-btn"><Trash2 size={13} className="mr-1" />Eliminar empresas vacías ({emptyCount})</Button>}
      {canManageCerts && <>
        <Button size="sm" variant="outline" className="h-8 text-xs bg-transparent text-white border-slate-500 hover:bg-slate-800 hover:text-white" disabled={!!busy} onClick={rebuild} data-testid="rebuild-certs-btn"><FileStack size={13} className="mr-1" />{busy === 'rebuild' ? 'Reconstruyendo...' : 'Reconstruir certificados'}</Button>
        <input ref={zipRef} type="file" accept=".zip" className="hidden" onChange={upload} data-testid="bulk-certs-input" />
        <Button size="sm" variant="outline" className="h-8 text-xs bg-transparent text-white border-slate-500 hover:bg-slate-800 hover:text-white" disabled={!!busy} onClick={() => zipRef.current?.click()} data-testid="bulk-certs-btn"><Upload size={13} className="mr-1" />{busy === 'zip' ? 'Procesando...' : 'Cargar certificados (ZIP)'}</Button>
      </>}
      <ResultDialog result={result} onClose={() => setResult(null)} />
    </div>
  );
};
