import { useState } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '../../ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../../ui/command';
import { Button } from '../../ui/button';
import { Check, ChevronsUpDown, Plus } from 'lucide-react';

// Selector de Marca filtrado estrictamente por Grupo Económico (si hay grupo).
export const BrandPicker = ({ brands, groupId, value, onSelect, onCreate, disabled, required }) => {
  const [open, setOpen] = useState(false);
  const options = groupId ? brands.filter(b => b.group_id === groupId) : brands;
  const current = brands.find(b => b.brand_id === value);
  return (
    <div className="flex gap-1.5">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button type="button" variant="outline" role="combobox" disabled={disabled} data-testid="client-marca-select"
            className={`h-9 flex-1 justify-between font-normal ${required && !value ? 'border-amber-400' : ''}`}>
            <span className="truncate">{current?.name || (required ? 'Seleccione la marca (obligatoria)' : 'Sin marca')}</span>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <Command>
            <CommandInput placeholder="Buscar marca..." className="h-9" data-testid="client-marca-search" />
            <CommandList>
              <CommandEmpty>No se encontró la marca.</CommandEmpty>
              <CommandGroup>
                <CommandItem value="__none__" onSelect={() => { onSelect(null); setOpen(false); }} data-testid="client-marca-option-none">
                  <Check className={`mr-2 h-4 w-4 ${!value ? 'opacity-100' : 'opacity-0'}`} />
                  <span className="text-slate-500 italic">Sin marca</span>
                </CommandItem>
                {options.map(b => (
                  <CommandItem key={b.brand_id} value={`${b.name} ${b.brand_id}`} onSelect={() => { onSelect(b); setOpen(false); }} data-testid={`client-marca-option-${b.brand_id}`}>
                    <Check className={`mr-2 h-4 w-4 ${value === b.brand_id ? 'opacity-100' : 'opacity-0'}`} />
                    <span className="truncate">{b.name}</span>
                    {!groupId && b.group_name && <span className="ml-auto text-[10px] text-slate-400 truncate">{b.group_name}</span>}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {onCreate && !disabled && (
        <Button type="button" variant="outline" size="sm" className="h-9 px-2" onClick={onCreate} title="Crear nueva marca" data-testid="client-marca-create-btn">
          <Plus size={14} />
        </Button>
      )}
    </div>
  );
};
