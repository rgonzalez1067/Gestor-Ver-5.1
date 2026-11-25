import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Download, Loader2, Mail, Paperclip } from 'lucide-react';
import api from '../../../utils/api';
import { Dialog, DialogContent, DialogTitle } from '../../ui/dialog';

const saveBlob = (blob, name) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
};
const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

// Visor de correo .eml adjunto en la bitácora: encabezados, cuerpo y adjuntos descargables.
export const EmailViewer = ({ projectId, ev, onClose, baseUrl }) => {
  const base = baseUrl || `/projects/${projectId}/bitacora/evidence/${ev.evidence_id}`;
  const emlBase = baseUrl ? `${baseUrl}/email` : `${base}/email`;
  const [mail, setMail] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    api.get(emlBase).then(r => setMail(r.data))
      .catch(e => { toast.error(e.response?.data?.detail || 'No se pudo abrir el correo'); onClose(); });
  }, [base]); // eslint-disable-line react-hooks/exhaustive-deps

  const download = async (path, name, key) => {
    setBusy(key);
    try { const r = await api.get(path, { responseType: 'blob' }); saveBlob(r.data, name); }
    catch { toast.error('No se pudo descargar el archivo'); }
    finally { setBusy(null); }
  };

  const Row = ({ label, value, testid }) => value ? (
    <div className="flex gap-2 text-xs"><span className="w-14 shrink-0 font-semibold text-slate-500">{label}</span><span className="break-all text-slate-800" data-testid={testid}>{value}</span></div>
  ) : null;

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="flex max-h-[92vh] w-[90vw] max-w-4xl flex-col gap-3 p-4" data-testid="email-viewer">
        <DialogTitle className="flex items-center gap-2 pr-8 text-base">
          <Mail size={18} className="shrink-0 text-indigo-600" />
          <span className="truncate" data-testid="email-viewer-subject">{mail?.subject || ev.filename}</span>
        </DialogTitle>
        {!mail ? <div className="py-10 text-center"><Loader2 className="mx-auto animate-spin text-slate-400" /></div> : (
          <>
            <div className="space-y-1 rounded-md border border-slate-200 bg-slate-50 p-3">
              <Row label="De" value={mail.from} testid="email-viewer-from" />
              <Row label="Para" value={mail.to} testid="email-viewer-to" />
              <Row label="CC" value={mail.cc} testid="email-viewer-cc" />
              <Row label="Fecha" value={mail.date} testid="email-viewer-date" />
            </div>
            {mail.attachments.length > 0 && (
              <div className="flex flex-wrap gap-2" data-testid="email-viewer-attachments">
                {mail.attachments.map(a => (
                  <button key={a.index} type="button" onClick={() => download(`${emlBase}/attachments/${a.index}`, a.filename, a.index)}
                    className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50"
                    data-testid={`email-viewer-attachment-${a.index}`}>
                    {busy === a.index ? <Loader2 size={12} className="animate-spin" /> : <Paperclip size={12} />}
                    {a.filename} <span className="text-slate-400">({kb(a.size)})</span>
                  </button>
                ))}
              </div>
            )}
            <div className="min-h-[300px] flex-1 overflow-hidden rounded-md border border-slate-200 bg-white">
              {mail.html
                ? <iframe title="Contenido del correo" sandbox="" srcDoc={mail.html} className="h-[55vh] w-full" data-testid="email-viewer-body" />
                : <pre className="h-[55vh] overflow-auto whitespace-pre-wrap p-3 text-sm text-slate-800" data-testid="email-viewer-body">{mail.text || '(Sin contenido)'}</pre>}
            </div>
            <div className="flex justify-end">
              <button type="button" onClick={() => download(base, ev.filename || 'correo.eml', 'eml')}
                className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900" data-testid="email-viewer-download-eml">
                {busy === 'eml' ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}Descargar .eml original
              </button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
