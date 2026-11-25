import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { Paperclip, Image as ImageIcon, Mail, X, Upload } from 'lucide-react';

const IMG_EXT = ['.jpg', '.jpeg', '.png', '.webp'];
const MAX = 10 * 1024 * 1024;
export const ATTACHMENT_FORMAT_ERROR = 'Formato no permitido: solo se admiten imágenes (.jpg, .jpeg, .png, .webp) o correos .eml';

const extOf = (n) => (n.match(/\.[^.]+$/)?.[0] || '').toLowerCase();
export const attachmentKind = (name) => (IMG_EXT.includes(extOf(name)) ? 'IMAGEN' : extOf(name) === '.eml' ? 'EML' : null);
const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

const validate = (f) => {
  if (!attachmentKind(f.name)) { toast.error(ATTACHMENT_FORMAT_ERROR); return false; }
  if (f.size > MAX) { toast.error('El archivo supera el tamaño máximo permitido de 10 MB'); return false; }
  return true;
};

const FileChip = ({ name, size, kind, onRemove, testid }) => (
  <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2" data-testid={testid}>
    {kind === 'IMAGEN' ? <ImageIcon size={16} className="text-emerald-600 shrink-0" /> : <Mail size={16} className="text-indigo-600 shrink-0" />}
    <span className="text-sm text-slate-800 truncate flex-1">{name}</span>
    {size ? <span className="text-[11px] text-slate-400">{kb(size)}</span> : null}
    <button type="button" onClick={onRemove} className="text-slate-400 hover:text-red-600" title="Quitar adjunto" data-testid={`${testid}-remove`}><X size={14} /></button>
  </div>
);

// Campo opcional «Documento de Respaldo / Anexo»: seleccionar, arrastrar o pegar (Ctrl+V).
export const AttachmentPicker = ({ file, onChange, existing, onRemoveExisting, testid = 'contact-attachment' }) => {
  const inputRef = useRef(null);
  const [over, setOver] = useState(false);
  const take = (f) => { if (f && validate(f)) onChange(f); };
  const onPaste = (e) => {
    const item = [...(e.clipboardData?.items || [])].find((i) => i.kind === 'file');
    if (!item) return;
    e.preventDefault();
    const blob = item.getAsFile();
    const ext = (blob.type.split('/')[1] || 'png').replace('jpeg', 'jpg');
    take(blob.name && blob.name !== 'image.png' ? blob : new File([blob], `captura_${Date.now()}.${ext}`, { type: blob.type }));
  };

  if (file) return <FileChip name={file.name} size={file.size} kind={attachmentKind(file.name)} onRemove={() => onChange(null)} testid={`${testid}-selected`} />;
  if (existing) return <FileChip name={existing.adjunto_nombre_original} size={existing.adjunto_size} kind={existing.adjunto_tipo} onRemove={onRemoveExisting} testid={`${testid}-existing`} />;

  return (
    <div tabIndex={0} onPaste={onPaste} onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); take(e.dataTransfer.files?.[0]); }}
      className={`cursor-pointer rounded-lg border-2 border-dashed px-4 py-4 text-center transition-colors outline-none focus:border-blue-400 ${over ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-white hover:bg-slate-50'}`}
      data-testid={`${testid}-dropzone`}>
      <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.webp,.eml,image/jpeg,image/png,image/webp,message/rfc822" className="hidden"
        onChange={(e) => { take(e.target.files?.[0]); e.target.value = ''; }} data-testid={`${testid}-input`} />
      <p className="text-sm text-slate-700 inline-flex items-center gap-1.5"><Paperclip size={14} /> <span className="font-medium text-blue-600">Seleccionar archivo</span> o arrastre y suelte aquí</p>
      <p className="text-[11px] text-slate-500 mt-1 inline-flex items-center gap-1"><Upload size={11} /> También puede hacer clic aquí y pegar una captura con Ctrl + V</p>
      <p className="text-[11px] text-slate-400">Formatos admitidos: imágenes (.jpg, .png, .webp) o .eml · Máximo 10 MB</p>
    </div>
  );
};
