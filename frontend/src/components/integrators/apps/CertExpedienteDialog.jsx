import { useCallback, useEffect, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Download, Eye, FolderOpen, Upload, Bot, User, Info } from 'lucide-react';
import api from '../../../utils/api';
import { toast } from 'sonner';

const ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp,.eml,.zip';
const VIEWABLE = /\.(pdf|jpe?g|png|webp)$/i;

export const CertExpedienteDialog = ({ cert, label, canUpload, onClose, onChanged }) => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);
  const fileRef = useRef(null);

  const load = useCallback(() => {
    if (!cert) return;
    api.get(`/integrators/certificates/${cert.certificate_id}/expediente`).then(r => setData(r.data)).catch(() => setData({ documents: [] }));
  }, [cert]);
  useEffect(() => { setData(null); load(); }, [load]);

  const fetchBlob = (d, inline) => api.get(`/integrators/expediente/${d.documento_id}/download`, { params: { inline }, responseType: 'blob' });
  const download = async (d) => {
    try {
      const r = await fetchBlob(d, false);
      const a = document.createElement('a'); a.href = URL.createObjectURL(r.data); a.download = d.nombre_documento; a.click();
    } catch { toast.error('No se pudo descargar el documento'); }
  };
  const view = async (d) => {
    try {
      const r = await fetchBlob(d, true);
      setPreview({ url: URL.createObjectURL(new Blob([r.data], { type: d.tipo_mime })), doc: d });
    } catch { toast.error('No se pudo abrir el documento'); }
  };
  const upload = async (e) => {
    const files = Array.from(e.target.files || []); e.target.value = '';
    if (!files.length) return;
    setBusy(true);
    try {
      const fd = new FormData(); files.forEach(f => fd.append('files', f));
      await api.post(`/integrators/certificates/${cert.certificate_id}/expediente`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success(`${files.length} documento(s) agregado(s) al expediente`); load(); onChanged?.();
    } catch (err) { toast.error(err.response?.data?.detail || 'Error al cargar documentos'); }
    finally { setBusy(false); }
  };

  const docs = data?.documents || [];
  return (
    <Dialog open={!!cert} onOpenChange={(o) => { if (!o) { setPreview(null); onClose(); } }}>
      <DialogContent className="max-w-3xl" data-testid="cert-expediente-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <FolderOpen size={18} className="text-amber-500" />Expediente Digital de Certificación — {label}
            {cert && <span className="text-xs font-normal text-slate-400">({new Date(cert.created_at).toLocaleDateString('es-VE')})</span>}
          </DialogTitle>
          <p className="text-xs text-slate-500">Aplicativo: {data?.aplicativo || '—'}{cert?.products_included?.length ? ` | Productos: ${cert.products_included.join(', ')}` : ''}</p>
        </DialogHeader>
        <div className="flex items-center justify-between">
          <p className="text-[11px] uppercase tracking-wide text-slate-400">Documentos y anexos del proceso ({docs.length})</p>
          {canUpload && <>
            <input ref={fileRef} type="file" multiple accept={ACCEPT} className="hidden" onChange={upload} data-testid="expediente-file-input" />
            <Button size="sm" variant="outline" disabled={busy} onClick={() => fileRef.current?.click()} data-testid="expediente-upload-btn">
              <Upload size={13} className="mr-1" />{busy ? 'Cargando...' : 'Cargar Documento Adicional'}
            </Button>
          </>}
        </div>
        {data === null ? <p className="text-xs text-slate-400">Cargando...</p> : docs.length === 0 ? (
          <p className="text-xs text-slate-400 py-4 text-center" data-testid="expediente-empty">Este expediente aún no tiene documentos.</p>
        ) : (
          <table className="w-full text-xs border border-slate-200 rounded-md overflow-hidden">
            <thead className="bg-slate-100 text-slate-500 text-[11px] uppercase"><tr>
              <th className="text-left px-3 py-2">Nombre del documento</th><th className="text-left px-3 py-2">Origen</th>
              <th className="text-left px-3 py-2">Fecha carga</th><th className="px-3 py-2" /></tr></thead>
            <tbody>
              {docs.map((d, i) => (
                <tr key={d.documento_id} className="border-t border-slate-100" data-testid={`expediente-doc-${d.documento_id}`}>
                  <td className="px-3 py-2 break-all">{i + 1}. {d.nombre_documento}</td>
                  <td className="px-3 py-2 whitespace-nowrap" data-testid={`expediente-origen-${d.documento_id}`}>
                    {d.origen_carga === 'AUTOMATICO'
                      ? <span className="inline-flex items-center gap-1 text-indigo-700"><Bot size={12} />Automático</span>
                      : <span className="inline-flex items-center gap-1 text-emerald-700"><User size={12} />Manual</span>}
                    <div className="text-[10px] text-slate-400">{d.usuario_carga_nombre}</div>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">{new Date(d.fecha_carga).toLocaleDateString('es-VE')}</td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    {VIEWABLE.test(d.nombre_documento) && <button className="p-1 text-slate-400 hover:text-brand-blue-600" title="Ver" onClick={() => view(d)} data-testid={`expediente-view-${d.documento_id}`}><Eye size={13} /></button>}
                    <button className="p-1 text-slate-400 hover:text-brand-blue-600" title="Descargar" onClick={() => download(d)} data-testid={`expediente-download-${d.documento_id}`}><Download size={13} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {preview && (
          <div className="border border-slate-200 rounded-md" data-testid="expediente-preview">
            <div className="flex justify-between items-center px-3 py-1.5 bg-slate-50 text-xs">
              <span className="font-semibold truncate">{preview.doc.nombre_documento}</span>
              <button className="text-slate-500 hover:text-slate-800" onClick={() => setPreview(null)} data-testid="expediente-preview-close">Cerrar vista</button>
            </div>
            {/pdf/.test(preview.doc.tipo_mime)
              ? <iframe title="preview" src={preview.url} className="w-full h-[420px]" />
              : <img alt={preview.doc.nombre_documento} src={preview.url} className="max-h-[420px] mx-auto object-contain" />}
          </div>
        )}
        <p className="text-[11px] text-slate-500 flex items-center gap-1"><Info size={12} className="text-blue-500" />Puede anexar recaudos faltantes en cualquier momento posterior al cierre.</p>
      </DialogContent>
    </Dialog>
  );
};
