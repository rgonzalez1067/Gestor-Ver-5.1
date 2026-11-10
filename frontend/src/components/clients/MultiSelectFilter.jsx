import { useState } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../ui/command';
import { Button } from '../ui/button';
import { Check, ChevronsUpDown } from 'lucide-react';

export const NONE_VALUE = '__none__';

export const MultiSelectFilter = ({ label, options, selected, onChange, testId }) => {
  const [open, setOpen] = useState(false);
  const toggle = (v) => onChange(selected.includes(v) ? selected.filter(x => x !== v) : [...selected, v]);
  const all = [{ value: NONE_VALUE, label: 'Sin asignar' }, ...options];
  const text = selected.length === 0 ? `Todos (${label})`
    : selected.length === 1 ? all.find(o => o.value === selected[0])?.label || label
    : `${label}: ${selected.length}`;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className={`h-9 w-52 justify-between font-normal ${selected.length ? 'border-indigo-400 text-indigo-700' : ''}`} data-testid={testId}>
          <span className="truncate">{text}</span>
          <ChevronsUpDown size={14} className="opacity-50 shrink-0" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-0" align="start">
        <Command>
          <CommandInput placeholder={`Buscar ${label.toLowerCase()}...`} data-testid={`${testId}-search`} />
          <CommandList>
            <CommandEmpty>Sin resultados</CommandEmpty>
            <CommandGroup>
              {all.map(o => (
                <CommandItem key={o.value} value={o.label} onSelect={() => toggle(o.value)} data-testid={`${testId}-option-${o.value}`}>
                  <Check size={14} className={`mr-2 ${selected.includes(o.value) ? 'opacity-100' : 'opacity-0'}`} />
                  <span className={o.value === NONE_VALUE ? 'italic text-slate-500' : ''}>{o.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
          {selected.length > 0 && (
            <button type="button" className="w-full text-xs text-slate-500 hover:bg-slate-50 py-2 border-t" onClick={() => onChange([])} data-testid={`${testId}-clear`}>
              Quitar filtro
            </button>
          )}
        </Command>
      </PopoverContent>
    </Popover>
  );
};
