import { useMemo, useState } from 'react';
import { Calendar, User, Zap, Images } from 'lucide-react';
import { Thumb, Lightbox } from './EvidenceGallery';

const FILTERS = [
  { key: 'all', label: 'Todo' },
  { key: 'image', label: 'Imágenes' },
  { key: 'pdf', label: 'PDF' },
  { key: 'email', label: 'Correos' },
];
const kindOf = (ev) => (ev.content_type === 'application/pdf' ? 'pdf' : ev.content_type === 'message/rfc822' ? 'email' : 'image');

// Galería: todas las imágenes y PDF adjuntos en la Bitácora del proyecto.
export const ProjectGallery = ({ projectId, bitacora }) => {
  const [filter, setFilter] = useState('all');
  const [open, setOpen] = useState(null);
  const items = useMemo(() => [...(bitacora || [])].reverse().flatMap(entry =>
    (entry.evidence || []).map(ev => ({ ev, entry }))), [bitacora]);
  const counts = Object.fromEntries(FILTERS.map(f => [f.key, f.key === 'all' ? items.length : items.filter(i => kindOf(i.ev) === f.key).length]));
  const shown = items.filter(i => filter === 'all' || kindOf(i.ev) === filter);

  return (
    <div data-testid="project-gallery">
      <div className="mb-3 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
        {FILTERS.map(f => (
          <button key={f.key} type="button" onClick={() => setFilter(f.key)} data-testid={`gallery-filter-${f.key}`}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${filter === f.key ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200' : 'text-slate-500 hover:text-slate-800'}`}>
            {f.label} <span className="tabular-nums text-slate-400" data-testid={`gallery-count-${f.key}`}>({counts[f.key]})</span>
          </button>
        ))}
      </div>
      {shown.length === 0 ? (
        <div className="py-10 text-center text-sm text-slate-400" data-testid="gallery-empty">
          <Images size={32} className="mx-auto mb-2 text-slate-300" />Sin archivos adjuntos en la bitácora
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" data-testid="gallery-grid">
          {shown.map(({ ev, entry }) => (
            <div key={ev.evidence_id} className="rounded-lg border border-slate-200 bg-white p-2" data-testid={`gallery-item-${ev.evidence_id}`}>
              <Thumb projectId={projectId} ev={ev} onOpen={setOpen} big />
              <p className="mt-1.5 truncate text-xs font-medium text-slate-700" title={ev.filename}>{ev.filename}</p>
              <p className="truncate text-[11px] text-slate-500" title={entry.text}>{entry.text}</p>
              <div className="mt-1 flex items-center justify-between gap-1 text-[10px] text-slate-400">
                <span className="flex items-center gap-0.5"><Calendar size={10} />{entry.execution_date}</span>
                <span className="flex min-w-0 items-center gap-0.5 truncate"><User size={10} />{entry.created_by_name}</span>
              </div>
              {entry.set_al_dia && <span className="mt-1 inline-flex items-center gap-0.5 rounded-full bg-emerald-100 px-1.5 text-[10px] font-semibold text-emerald-700"><Zap size={9} />Al día</span>}
            </div>
          ))}
        </div>
      )}
      <Lightbox open={open} onClose={() => setOpen(null)} />
    </div>
  );
};
