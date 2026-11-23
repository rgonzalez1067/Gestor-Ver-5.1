import { useState } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../ui/command';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { ChevronsUpDown, Check, Plus, Info, X } from 'lucide-react';

export const TIPOS_REFERENTE = [['PERSONA', 'Persona'], ['AREA', 'Área'], ['EMPRESA', 'Empresa']];
export const EMPTY_NUEVO = { nombre_referente: '', tipo_referente: 'PERSONA', empresa: '', persona: '' };

export const referenteLabel = (r) => {
  if (!r) return '';
  const extra = [r.empresa, r.persona].filter(Boolean).join(' / ');
  return extra ? `${r.nombre_referente} — (${extra})` : r.nombre_referente;
};

const QuickReferenteForm = ({ value, onChange, onCancel }) => {
  const set = (k) => (e) => onChange({ ...value, [k]: e.target.value });
  return (
    <div className="mt-2 rounded-md border border-blue-200 bg-blue-50/50 p-3 space-y-2.5" data-testid="quick-referente-form">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Registrar nuevo referente</p>
        <button type="button" onClick={onCancel} className="text-slate-400 hover:text-slate-700" data-testid="quick-referente-cancel"><X size={14} /></button>
      </div>
      <div>
        <Label className="text-xs">Nombre del Referente *</Label>
        <Input className="h-8 bg-white" maxLength={150} value={value.nombre_referente} onChange={set('nombre_referente')} placeholder="Ej: Pedro Gómez" data-testid="quick-referente-name" />
      </div>
      <div>
        <Label className="text-xs">Tipo *</Label>
        <div className="flex gap-4 mt-1">
          {TIPOS_REFERENTE.map(([k, label]) => (
            <label key={k} className="flex items-center gap-1.5 text-sm cursor-pointer">
              <input type="radio" name="tipo_referente" checked={value.tipo_referente === k} onChange={() => onChange({ ...value, tipo_referente: k })} data-testid={`quick-referente-tipo-${k}`} />{label}
            </label>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div><Label className="text-xs">Empresa (Opcional)</Label><Input className="h-8 bg-white" maxLength={150} value={value.empresa} onChange={set('empresa')} data-testid="quick-referente-empresa" /></div>
        <div><Label className="text-xs">Persona (Opcional)</Label><Input className="h-8 bg-white" maxLength={150} value={value.persona} onChange={set('persona')} data-testid="quick-referente-persona" /></div>
      </div>
      <p className="text-[11px] text-blue-700 flex items-center gap-1.5"><Info size={12} />Este registro se guardará automáticamente en la BD de Referentes.</p>
    </div>
  );
};

export const ReferentePicker = ({ referentes, canCreate, value, onChange, testId = 'referente-picker' }) => {
  const [open, setOpen] = useState(false);
  const selected = referentes.find((r) => r.referente_id === value.referente_id);
  const pick = (patch) => { onChange(patch); setOpen(false); };
  return (
    <div>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button type="button" className="flex h-9 w-full items-center justify-between rounded-md border border-blue-200 bg-blue-50/50 px-3 text-sm text-left" data-testid={testId}>
            <span className={`truncate ${selected || value.nuevo ? 'text-slate-800' : 'text-slate-400'}`}>
              {value.nuevo ? 'Otro (nuevo referente)' : selected ? referenteLabel(selected) : 'Seleccione un Referente...'}
            </span>
            <ChevronsUpDown size={14} className="text-slate-400 shrink-0" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="p-0 w-[--radix-popover-trigger-width] min-w-[320px]" align="start">
          <Command filter={(v, s) => (v.toLowerCase().includes(s.toLowerCase()) || v === '__otro__' ? 1 : 0)}>
            <CommandInput placeholder="Buscar referente..." data-testid={`${testId}-search`} />
            <CommandList className="max-h-64">
              <CommandEmpty>Sin coincidencias</CommandEmpty>
              <CommandGroup>
                {canCreate && (
                  <CommandItem value="__otro__" onSelect={() => pick({ referente_id: '', nuevo: { ...EMPTY_NUEVO } })} className="text-blue-700 font-medium" data-testid={`${testId}-otro`}>
                    <Plus size={14} className="mr-2" />Otro (Registrar nuevo referente)
                  </CommandItem>
                )}
                {value.referente_id && (
                  <CommandItem value="__ninguno__ sin referente" onSelect={() => pick({ referente_id: '', nuevo: null })} className="text-slate-500" data-testid={`${testId}-none`}>Sin referente</CommandItem>
                )}
                {referentes.map((r) => (
                  <CommandItem key={r.referente_id} value={`${referenteLabel(r)} ${r.referente_id}`} onSelect={() => pick({ referente_id: r.referente_id, nuevo: null })} data-testid={`${testId}-option-${r.referente_id}`}>
                    <Check size={14} className={`mr-2 ${value.referente_id === r.referente_id ? 'opacity-100' : 'opacity-0'}`} />{referenteLabel(r)}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {value.nuevo && <QuickReferenteForm value={value.nuevo} onChange={(nuevo) => onChange({ ...value, nuevo })} onCancel={() => onChange({ referente_id: '', nuevo: null })} />}
    </div>
  );
};

export const referentePayload = (value) => (value.nuevo ? { nuevo_referente: value.nuevo } : value.referente_id ? { referente_id: value.referente_id } : {});
