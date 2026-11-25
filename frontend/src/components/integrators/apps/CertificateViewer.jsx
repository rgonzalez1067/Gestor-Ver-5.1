import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Download, Loader2 } from 'lucide-react';
import api from '../../../utils/api';

export const CertificateViewer = ({ cert, onClose, onDownload }) => {
  const [url, setUrl] = useState('');
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!cert) return undefined;
    let objectUrl = '';
    setUrl(''); setError(false);
    api.get(`/integrators/certificates/${cert.certificate_id}/download`, { params: { inline: true }, responseType: 'blob' })
      .then((r) => { objectUrl = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' })); setUrl(objectUrl); })
      .catch(() => setError(true));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [cert]);

  return (
    <Dialog open={!!cert} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-5xl w-[94vw] h-[90vh] flex flex-col gap-3" data-testid="cert-viewer-dialog">
        <DialogHeader className="flex-row items-center justify-between space-y-0 pr-8">
          <DialogTitle className="text-base truncate">{cert?.original_name || 'Certificado'}</DialogTitle>
          <Button size="sm" variant="outline" onClick={() => onDownload(cert)} data-testid="cert-viewer-download"><Download size={14} className="mr-1.5" />Descargar</Button>
        </DialogHeader>
        <div className="flex-1 min-h-0 rounded-md border border-slate-200 bg-slate-100 overflow-hidden">
          {error ? <p className="p-8 text-center text-sm text-red-600">No se pudo cargar el certificado.</p>
            : !url ? <div className="h-full flex items-center justify-center"><Loader2 className="animate-spin text-slate-400" /></div>
              : <iframe title="Vista previa del certificado" src={`${url}#toolbar=1&view=FitH`} className="w-full h-full" data-testid="cert-viewer-frame" />}
        </div>
      </DialogContent>
    </Dialog>
  );
};
