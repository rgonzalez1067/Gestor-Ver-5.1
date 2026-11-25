import { ChevronDown } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Checkbox } from '../ui/checkbox';

// Selector múltiple: [] = Todos.
export const MultiPick = ({ label, value, onChange, options, testid }) => {
  const toggle = (v) => onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);
  const text = value.length === 0 ? 'Todos' : value.length === 1 ? value[0] : `${value.length} seleccionados`;
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <span className="text-[11px] font-medium text-slate-500">{label}</span>
      <Popover>
        <PopoverTrigger asChild>
          <button type="button" className="flex h-9 items-center justify-between gap-1 rounded-md border border-input bg-background px-3 text-sm" data-testid={testid}>
            <span className="truncate">{text}</span><ChevronDown size={14} className="shrink-0 opacity-50" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-1" align="start" data-testid={`${testid}-menu`}>
          <label className="flex items-center gap-2 rounded px-2 py-1.5 text-sm font-medium hover:bg-slate-100 cursor-pointer border-b border-slate-100">
            <Checkbox checked={value.length === 0} onCheckedChange={() => onChange([])} data-testid={`${testid}-all`} />Todos
          </label>
          <div className="max-h-64 overflow-auto">
            {options.map((o) => (
              <label key={o} className="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-100 cursor-pointer">
                <Checkbox checked={value.includes(o)} onCheckedChange={() => toggle(o)} data-testid={`${testid}-opt-${o}`} /><span className="truncate">{o}</span>
              </label>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
};
