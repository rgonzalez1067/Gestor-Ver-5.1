import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { Download, Upload, FolderArchive, Loader2, CheckCircle2 } from 'lucide-react';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const mb = (b) => `${((b || 0) / (1024 * 1024)).toFixed(1)} MB`;

export const FilesBackupCard = () => {
  const [busy, setBusy] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState('');
  const [ready, setReady] = useState(null);
  const [result, setResult] = useState(null);
  const fileRef = useRef(null);

  const build = async () => {
    setBusy('export'); setReady(null); setPct(0);
    try {
      const { data: b } = await api.post('/admin/files-backup/build');
      setStatus('Buscando y empaquetando archivos de la nube...');
      let st;
      for (;;) {
        await sleep(2500);
        ({ data: st } = await api.get('/admin/full-backup/build-status', { params: { job_id: b.job_id } }));
        if (st.status !== 'building') break;
        if (st.total_collections) {
          setPct(Math.min(99, Math.round((st.progress_collections / st.total_collections) * 100)));
          setStatus(`Empaquetando ${st.progress_collections} de ${st.total_collections} archivos...`);
        }
      }
      if (st.status !== 'ready') throw new Error(st.error || 'No se pudo armar el respaldo de archivos');
      setReady({ jobId: b.job_id, size: st.size_bytes, files: st.collections });
      toast.success('Respaldo de archivos listo');
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(null); setPct(0); setStatus(''); }
  };

  const download = async () => {
    try {
      const { data: tk } = await api.post('/admin/full-backup/export-ticket', { job_id: ready.jobId });
      const a = document.createElement('a');
      a.href = `${process.env.REACT_APP_BACKEND_URL}/api/admin/full-backup/export?ticket=${encodeURIComponent(tk.ticket)}`;
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al descargar'); }
  };

  const restore = async (e) => {
    const file = e.target.files?.[0]; e.target.value = '';
    if (!file) return;
    if (!window.confirm(`¿Restaurar los archivos de "${file.name}" al almacenamiento? Los archivos con la misma ruta se reemplazan.`)) return;
    setBusy('restore'); setResult(null); setPct(0);
    try {
      const { data: init } = await api.post('/admin/full-backup/upload-init');
      const CHUNK = 4 * 1024 * 1024, total = Math.max(1, Math.ceil(file.size / CHUNK));
      for (let i = 0; i < total; i++) {
        const fd = new FormData();
        fd.append('upload_id', init.upload_id); fd.append('chunk_index', i); fd.append('file', file.slice(i * CHUNK, (i + 1) * CHUNK), 'chunk.part');
        await api.post('/admin/full-backup/upload-chunk', fd);
        setPct(Math.round(((i + 1) / total) * 50)); setStatus(`Subiendo respaldo... ${Math.round(((i + 1) / total) * 100)}%`);
      }
      const fd = new FormData(); fd.append('upload_id', init.upload_id);
      const { data: job } = await api.post('/admin/files-backup/restore', fd);
      let st;
      for (;;) {
        await sleep(2500);
        ({ data: st } = await api.get('/admin/files-backup/restore-status', { params: { job_id: job.job_id } }));
        if (st.total) { setPct(50 + Math.round((st.done / st.total) * 50)); setStatus(`Restaurando ${st.done} de ${st.total} archivos...`); }
        if (st.status !== 'running') break;
      }
      if (st.status !== 'done') throw new Error(st.error || 'Error al restaurar archivos');
      setResult(st); toast.success(`${st.restored} archivos restaurados`);
    } catch (err) { toast.error(err.response?.data?.detail || err.message); }
    finally { setBusy(null); setPct(0); setStatus(''); }
  };

  return (
    <div className="bg-white rounded-xl border border-amber-200 shadow-sm mb-6 overflow-hidden" data-testid="files-backup-card">
      <div className="p-5">
        <div className="flex items-start gap-3">
          <FolderArchive size={22} className="text-amber-600 mt-0.5" />
          <div className="flex-1">
            <h2 className="text-sm font-semibold text-slate-900">Respaldo de Archivos (almacenamiento en la nube)</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Complementa el Respaldo Total: incluye los archivos reales (Expedientes de Certificación, adjuntos de Contacto Inicial,
              comunicaciones, logos, anexos de cotizaciones y proyectos, PDFs). Restáuralo en el servidor destino después de la base de datos.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 mt-4">
          <Button onClick={build} disabled={!!busy} className="bg-amber-600 hover:bg-amber-700 text-white" data-testid="files-backup-export-btn">
            {busy === 'export' ? <Loader2 size={15} className="mr-1.5 animate-spin" /> : <Download size={15} className="mr-1.5" />}Generar respaldo de archivos
          </Button>
          <input ref={fileRef} type="file" accept=".zip" className="hidden" onChange={restore} data-testid="files-backup-file-input" />
          <Button variant="outline" disabled={!!busy} onClick={() => fileRef.current?.click()} data-testid="files-backup-restore-btn">
            {busy === 'restore' ? <Loader2 size={15} className="mr-1.5 animate-spin" /> : <Upload size={15} className="mr-1.5" />}Restaurar archivos desde .zip
          </Button>
        </div>
        {busy && <div className="mt-4" data-testid="files-backup-progress"><Progress value={pct} /><p className="text-[11px] text-slate-500 mt-1">{status}</p></div>}
        {ready && !busy && (
          <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/60 p-3" data-testid="files-backup-ready">
            <p className="text-sm font-semibold text-emerald-800 flex items-center gap-1.5"><CheckCircle2 size={15} />Listo: {ready.files} archivos ({mb(ready.size)})</p>
            <Button onClick={download} className="mt-2 bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="files-backup-download-btn">
              <Download size={15} className="mr-1.5" />Descargar respaldo de archivos (.zip)
            </Button>
          </div>
        )}
        {result && !busy && (
          <p className="mt-4 text-sm text-emerald-700" data-testid="files-backup-result">
            Restaurados {result.restored} de {result.total} archivos{result.error_count ? ` (${result.error_count} con error)` : ''}.
          </p>
        )}
      </div>
    </div>
  );
};
