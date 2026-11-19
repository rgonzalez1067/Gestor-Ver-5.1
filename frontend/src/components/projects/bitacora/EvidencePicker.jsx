import { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { ImagePlus, X } from 'lucide-react';

export const EVIDENCE_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
export const EVIDENCE_MAX_MB = 5;
export const EVIDENCE_MAX_FILES = 5;
const RULES = 'Formatos: JPG, PNG, WEBP · Tamaño máx.: 5 MB · Hasta 5 imágenes';

// Valida y agrega archivos (selector, arrastrar o Ctrl+V) respetando límites.
export const addEvidenceFiles = (incoming, current, setFiles) => {
  const ok = [];
  for (const f of incoming) {
    if (!EVIDENCE_TYPES.includes(f.type)) { toast.error(`"${f.name || 'archivo'}" no permitido. ${RULES}`); continue; }
    if (f.size > EVIDENCE_MAX_MB * 1024 * 1024) { toast.error(`"${f.name || 'imagen'}" supera 5 MB. ${RULES}`); continue; }
    ok.push(f.name ? f : new File([f], `captura_${Date.now()}.png`, { type: f.type }));
  }
  const room = EVIDENCE_MAX_FILES - current.length;
  if (ok.length > room) toast.error(`Máximo ${EVIDENCE_MAX_FILES} imágenes por entrada`);
  if (room > 0 && ok.length) setFiles([...current, ...ok.slice(0, room)]);
};

export const EvidencePicker = ({ files, setFiles, disabled }) => {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const previews = useMemo(() => files.map(f => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach(u => URL.revokeObjectURL(u)), [previews]);
  const onDrop = (e) => { e.preventDefault(); setDrag(false); if (!disabled) addEvidenceFiles([...e.dataTransfer.files], files, setFiles); };

  return (
    <div data-testid="bitacora-evidence-picker">
      <label className="text-xs font-medium text-slate-600">Evidencia Visual (Captura de Correo / Soporte)</label>
      <div tabIndex={0} onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}
        className={`mt-1 flex flex-wrap items-center gap-3 rounded-lg border-2 border-dashed px-3 py-2.5 text-xs outline-none transition-colors focus:border-brand-green-500 ${drag ? 'border-brand-green-500 bg-brand-green-50' : 'border-slate-300 bg-white'}`}
        data-testid="bitacora-evidence-dropzone">
        <button type="button" disabled={disabled || files.length >= EVIDENCE_MAX_FILES} onClick={() => inputRef.current?.click()}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-slate-50 px-2.5 py-1.5 font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
          data-testid="bitacora-evidence-select-btn">
          <ImagePlus size={14} />Seleccionar imagen
        </button>
        <span className="text-slate-500">o arrastre y suelte aquí · pegue con <kbd className="rounded border bg-slate-100 px-1 font-mono">Ctrl+V</kbd></span>
        <span className="w-full text-[11px] text-slate-400">{RULES}</span>
        <input ref={inputRef} type="file" accept="image/png, image/jpeg, image/webp" multiple hidden
          onChange={(e) => { addEvidenceFiles([...e.target.files], files, setFiles); e.target.value = ''; }} data-testid="bitacora-evidence-input" />
      </div>
      {files.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2" data-testid="bitacora-evidence-previews">
          {files.map((f, i) => (
            <div key={previews[i]} className="relative h-16 w-24 overflow-hidden rounded-md border border-slate-200 bg-slate-100" data-testid={`bitacora-evidence-preview-${i}`}>
              <img src={previews[i]} alt={f.name} className="h-full w-full object-cover" />
              <button type="button" onClick={() => setFiles(files.filter((_, j) => j !== i))} disabled={disabled}
                className="absolute right-0.5 top-0.5 rounded-full bg-slate-900/70 p-0.5 text-white hover:bg-red-600" data-testid={`bitacora-evidence-remove-${i}`}>
                <X size={11} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
