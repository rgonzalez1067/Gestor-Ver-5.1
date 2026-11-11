import { useState } from 'react';
import { History, Loader2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import api from '../../utils/api';
import { formatDate } from '../../utils/dateFormat';

const daysLabel = (d) => (d === 1 ? '1 día' : `${d} días`);

const TimelineItem = ({ item, idx }) => (
  <li className="relative pl-5 pb-3 last:pb-0" data-testid={`assignment-timeline-item-${idx}`}>
    <span className={`absolute left-0 top-1 w-2.5 h-2.5 rounded-full ${item.current ? 'bg-violet-600 ring-2 ring-violet-200' : 'bg-slate-300'}`} />
    <div className="flex items-baseline justify-between gap-2">
      <p className={`text-sm ${item.current ? 'font-semibold text-violet-700' : 'font-medium text-slate-700'}`}>{item.name}</p>
      <span className="text-[11px] font-semibold text-slate-600 whitespace-nowrap">{daysLabel(item.days)}</span>
    </div>
    <p className="text-[11px] text-slate-500">
      {item.approx ? 'Desde ~' : 'Desde '}{formatDate(item.at)} · {item.current ? 'actual' : `hasta ${formatDate(item.until)}`}
    </p>
    {item.by && <p className="text-[10px] text-slate-400">Asignado por {item.by}</p>}
  </li>
);

export const AssignmentTimelineButton = ({ projectId }) => {
  const [items, setItems] = useState(null);
  const load = async (open) => {
    if (!open || items) return;
    try {
      const res = await api.get(`/projects/${projectId}/assignment-timeline`);
      setItems(res.data.timeline || []);
    } catch {
      setItems([]);
    }
  };
  return (
    <Popover onOpenChange={load}>
      <PopoverTrigger asChild>
        <button type="button" title="Historial de implementadores"
          className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-violet-600 transition-colors"
          data-testid="assignment-timeline-btn">
          <History size={12} /> Historial
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80" align="start" data-testid="assignment-timeline-popover">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Implementadores del proyecto</p>
        {items === null ? (
          <div className="flex justify-center py-3"><Loader2 size={16} className="animate-spin text-slate-400" /></div>
        ) : items.length === 0 ? (
          <p className="text-xs text-slate-500" data-testid="assignment-timeline-empty">Sin asignaciones registradas</p>
        ) : (
          <ol className="relative border-l border-slate-200 ml-1 pl-0">
            {items.map((it, i) => <TimelineItem key={`${it.at}-${i}`} item={it} idx={i} />)}
          </ol>
        )}
      </PopoverContent>
    </Popover>
  );
};
