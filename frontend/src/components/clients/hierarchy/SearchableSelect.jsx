import { useState } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '../../ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../../ui/command';
import { Button } from '../../ui/button';
import { Check, ChevronsUpDown } from 'lucide-react';

// Select con búsqueda. options: [{id, name}]; onChange(option|null). emptyLabel = opción "heredar/ninguno".
export const SearchableSelect = ({ options, value, onChange, emptyLabel, disabled, testId, placeholder = 'Buscar...' }) => {
  const [open, setOpen] = useState(false);
  const current = options.find(o => o.id === value);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button type="button" variant="outline" role="combobox" disabled={disabled} data-testid={testId}
          className="h-9 w-full min-w-0 justify-between font-normal">
          <span className={`truncate ${current ? '' : 'text-slate-500'}`}>{current?.name || emptyLabel}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-[240px] p-0" align="start">
        <Command>
          <CommandInput placeholder={placeholder} className="h-9" data-testid={`${testId}-search`} />
          <CommandList>
            <CommandEmpty>Sin resultados.</CommandEmpty>
            <CommandGroup>
              <CommandItem value="__none__" onSelect={() => { onChange(null); setOpen(false); }} data-testid={`${testId}-option-none`}>
                <Check className={`mr-2 h-4 w-4 ${!value ? 'opacity-100' : 'opacity-0'}`} />
                <span className="text-slate-500 italic truncate">{emptyLabel}</span>
              </CommandItem>
              {options.map(o => (
                <CommandItem key={o.id} value={`${o.name} ${o.id}`} onSelect={() => { onChange(o); setOpen(false); }} data-testid={`${testId}-option-${o.id}`}>
                  <Check className={`mr-2 h-4 w-4 ${value === o.id ? 'opacity-100' : 'opacity-0'}`} />
                  <span className="truncate">{o.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
};
