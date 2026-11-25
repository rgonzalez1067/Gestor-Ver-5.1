import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Download, Image as ImageIcon, Mail, Loader2 } from 'lucide-react';
import api from '../../utils/api';
import { Dialog, DialogContent, DialogTitle } from '../ui/dialog';
import { EmailViewer } from '../projects/bitacora/EmailViewer';

const saveBlob = (blob, name) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
};

export const downloadContactAttachment = async (c) => {
  try {
    const r = await api.get(`/initial-contacts/${c.contact_id}/attachment`, { responseType: 'blob' });
    saveBlob(r.data, c.adjunto_nombre_original || 'adjunto');
  } catch { toast.error('No se pudo descargar el archivo'); }
};

const ImageLightbox = ({ contact, onClose }) => {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    let url;
    api.get(`/initial-contacts/${contact.contact_id}/attachment?inline=true`, { responseType: 'blob' })
      .then((r) => { url = URL.createObjectURL(r.data); setSrc(url); })
      .catch(() => { toast.error('No se pudo abrir la imagen'); onClose(); });
    return () => url && URL.revokeObjectURL(url);
  }, [contact.contact_id]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="flex max-h-[94vh] w-[92vw] max-w-5xl flex-col gap-3 p-4" data-testid="attachment-lightbox">
        <DialogTitle className="flex items-center gap-2 pr-8 text-base"><ImageIcon size={18} className="text-emerald-600" /><span className="truncate">{contact.adjunto_nombre_original}</span></DialogTitle>
        <div className="flex min-h-[300px] flex-1 items-center justify-center overflow-auto rounded-md bg-slate-900/90">
          {src ? <img src={src} alt={contact.adjunto_nombre_original} className="max-h-[75vh] max-w-full object-contain" data-testid="attachment-lightbox-img" /> : <Loader2 className="animate-spin text-slate-300" />}
        </div>
        <div className="flex justify-end">
          <button type="button" onClick={() => downloadContactAttachment(contact)} className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900" data-testid="attachment-lightbox-download"><Download size={12} />Descargar imagen</button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export const AttachmentViewer = ({ contact, onClose }) => (contact.adjunto_tipo === 'EML'
  ? <EmailViewer baseUrl={`/initial-contacts/${contact.contact_id}/attachment`} ev={{ filename: contact.adjunto_nombre_original }} onClose={onClose} />
  : <ImageLightbox contact={contact} onClose={onClose} />);

// Badge de la grilla: indica tipo de adjunto y abre el visor.
export const AttachmentBadge = ({ contact, onOpen }) => {
  if (!contact.adjunto_tipo) return null;
  const isImg = contact.adjunto_tipo === 'IMAGEN';
  return (
    <button type="button" onClick={() => onOpen(contact)} title={`${isImg ? 'Imagen' : 'Correo .eml'}: ${contact.adjunto_nombre_original}`}
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold border shrink-0 ${isImg ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100' : 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100'}`}
      data-testid={`contact-attachment-badge-${contact.contact_id}`}>
      {isImg ? <ImageIcon size={11} /> : <Mail size={11} />}{isImg ? 'Imagen' : 'Correo .eml'}
    </button>
  );
};
