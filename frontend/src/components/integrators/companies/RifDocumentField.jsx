import { useRef, useState } from 'react';
import { Button } from '../../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Eye, Download, ScanLine, FileText, X } from 'lucide-react';
import api from '../../../utils/api';
import { toast } from 'sonner';

const ACCEPT = '.pdf,.jpg,.jpeg,.png';

export const fetchRifBlob = async (empresaId) => {
  const res = await api.get(`/integrator-companies/${empresaId}/rif-document`, { responseType: 'blob' });
  return URL.createObjectURL(res.data);
};

export const RifDocumentField = ({ empresaId, filename, pendingFile, onPick }) => {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(null);

  const openPreview = async () => {
    try {
      if (pendingFile) setPreview({ url: URL.createObjectURL(pendingFile), type: pendingFile.type, name: pendingFile.name });
      else setPreview({ url: await fetchRifBlob(empresaId), type: /\.pdf$/i.test(filename || '') ? 'application/pdf' : 'image', name: filename });
    } catch { toast.error('No se pudo cargar el RIF escaneado'); }
  };
  const download = async () => {
    try {
      const a = document.createElement('a');
      a.href = await fetchRifBlob(empresaId); a.download = filename || 'RIF'; a.click();
    } catch { toast.error('No se pudo descargar el RIF'); }
  };
  const pick = (e) => {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    if (!/\.(pdf|jpe?g|png)$/i.test(f.name)) { toast.error('Formato no permitido. Use PDF, JPG o PNG'); return; }
    if (f.size > 10 * 1024 * 1024) { toast.error('El archivo supera 10 MB'); return; }
    onPick(f);
  };
  const shown = pendingFile?.name || filename;

  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-3 flex items-center gap-3 flex-wrap" data-testid="rif-document-field">
      <ScanLine size={18} className="text-brand-blue-600" />
      <div className="flex-1 min-w-[160px]">
        <p className="text-xs font-semibold text-slate-700">Documento RIF Escaneado <span className="font-normal text-slate-400">(PDF / JPG / PNG)</span></p>
        <p className="text-xs text-slate-500 truncate" data-testid="rif-document-name">
          {shown ? <><FileText size={12} className="inline mr-1" />{shown}{pendingFile && <span className="ml-1 text-amber-600">(se cargará al guardar)</span>}</> : 'Sin documento cargado'}
        </p>
      </div>
      <input ref={inputRef} type="file" accept={ACCEPT} className="hidden" onChange={pick} data-testid="rif-document-input" />
      <Button type="button" size="sm" variant="outline" onClick={() => inputRef.current?.click()} data-testid="rif-document-upload-btn">{shown ? 'Reemplazar' : 'Cargar RIF'}</Button>
      {pendingFile && <Button type="button" size="sm" variant="ghost" className="text-red-500" onClick={() => onPick(null)} data-testid="rif-document-clear-btn"><X size={14} /></Button>}
      {shown && <Button type="button" size="sm" variant="outline" onClick={openPreview} data-testid="rif-document-preview-btn"><Eye size={14} className="mr-1" />Ver</Button>}
      {filename && !pendingFile && <Button type="button" size="sm" variant="outline" onClick={download} data-testid="rif-document-download-btn"><Download size={14} className="mr-1" />Descargar</Button>}
      <Dialog open={!!preview} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent className="max-w-4xl" data-testid="rif-preview-dialog">
          <DialogHeader><DialogTitle className="text-base">RIF escaneado · {preview?.name}</DialogTitle></DialogHeader>
          {preview && (preview.type === 'application/pdf'
            ? <iframe title="RIF" src={preview.url} className="w-full h-[70vh] rounded border" data-testid="rif-preview-pdf" />
            : <img src={preview.url} alt="RIF" className="max-h-[70vh] mx-auto rounded border" data-testid="rif-preview-img" />)}
        </DialogContent>
      </Dialog>
    </div>
  );
};
