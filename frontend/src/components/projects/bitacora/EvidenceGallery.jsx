import { useEffect, useState } from 'react';
import api from '../../../utils/api';
import { Dialog, DialogContent, DialogTitle } from '../../ui/dialog';
import { Download, ZoomIn, ZoomOut, Zap, Loader2, FileText } from 'lucide-react';

const cache = new Map();
const useEvidenceUrl = (projectId, ev) => {
  const key = `${projectId}/${ev.evidence_id}`;
  const [url, setUrl] = useState(cache.get(key) || null);
  useEffect(() => {
    if (cache.has(key)) return;
    let alive = true;
    api.get(`/projects/${projectId}/bitacora/evidence/${ev.evidence_id}`, { responseType: 'blob' })
      .then(r => { const u = URL.createObjectURL(r.data); cache.set(key, u); if (alive) setUrl(u); })
      .catch(() => {});
    return () => { alive = false; };
  }, [key, projectId, ev.evidence_id]);
  return url;
};

const Thumb = ({ projectId, ev, onOpen }) => {
  const url = useEvidenceUrl(projectId, ev);
  if (ev.content_type === 'application/pdf') return (
    <button type="button" onClick={() => url && window.open(url, '_blank')} title={ev.filename}
      className="flex h-14 w-20 flex-col items-center justify-center gap-0.5 rounded-md border border-red-200 bg-red-50 px-1 text-red-600 transition-transform hover:scale-105 hover:shadow"
      data-testid={`bitacora-evidence-thumb-${ev.evidence_id}`}>
      {url ? <><FileText size={18} /><span className="w-full truncate text-center text-[9px]">{ev.filename}</span></> : <Loader2 size={14} className="animate-spin" />}
    </button>
  );
  return (
    <button type="button" onClick={() => url && onOpen({ url, ev })} title={ev.filename}
      className="h-14 w-20 overflow-hidden rounded-md border border-slate-200 bg-slate-100 transition-transform hover:scale-105 hover:shadow"
      data-testid={`bitacora-evidence-thumb-${ev.evidence_id}`}>
      {url ? <img src={url} alt={ev.filename} className="h-full w-full object-cover" /> : <Loader2 size={14} className="mx-auto animate-spin text-slate-400" />}
    </button>
  );
};

const Lightbox = ({ open, onClose }) => {
  const [zoom, setZoom] = useState(1);
  useEffect(() => { setZoom(1); }, [open]);
  return (
    <Dialog open={!!open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="w-[90vw] max-w-[90vw] p-3" data-testid="bitacora-evidence-lightbox">
        <DialogTitle className="flex items-center gap-2 pr-8 text-sm">
          <span className="truncate">{open?.ev.filename}</span>
          <span className="ml-auto flex items-center gap-1">
            <button type="button" onClick={() => setZoom(z => Math.max(0.5, z - 0.25))} className="rounded p-1.5 hover:bg-slate-100" data-testid="lightbox-zoom-out"><ZoomOut size={16} /></button>
            <span className="w-12 text-center text-xs tabular-nums" data-testid="lightbox-zoom-level">{Math.round(zoom * 100)}%</span>
            <button type="button" onClick={() => setZoom(z => Math.min(4, z + 0.25))} className="rounded p-1.5 hover:bg-slate-100" data-testid="lightbox-zoom-in"><ZoomIn size={16} /></button>
            <a href={open?.url} download={open?.ev.filename || 'evidencia'} className="rounded p-1.5 hover:bg-slate-100" data-testid="lightbox-download"><Download size={16} /></a>
          </span>
        </DialogTitle>
        <div className="max-h-[78vh] overflow-auto rounded bg-slate-900/90">
          {open && <img src={open.url} alt={open.ev.filename} style={zoom === 1 ? { maxWidth: '100%' } : { width: `${zoom * 100}%`, maxWidth: 'none' }} className="mx-auto block" data-testid="lightbox-image" />}
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Miniaturas clicables + insignia "Al día" de una entrada de bitácora.
export const EntryEvidence = ({ projectId, entry }) => {
  const [open, setOpen] = useState(null);
  const ev = entry.evidence || [];
  if (!ev.length && !entry.set_al_dia) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {entry.set_al_dia && (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700" data-testid={`bitacora-al-dia-badge-${entry.entry_id}`}>
          <Zap size={11} />Estatus actualizado a: Al día
        </span>
      )}
      {ev.length > 0 && (
        <div className="flex flex-wrap gap-2" data-testid={`bitacora-evidence-${entry.entry_id}`}>
          {ev.map(e => <Thumb key={e.evidence_id} projectId={projectId} ev={e} onOpen={setOpen} />)}
        </div>
      )}
      <Lightbox open={open} onClose={() => setOpen(null)} />
    </div>
  );
};
