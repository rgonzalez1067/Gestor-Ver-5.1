import { Search, RotateCcw, ChevronDown } from 'lucide-react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

const Field = ({ label, children }) => (
  <div className="flex flex-col gap-1 min-w-0">
    <label className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</label>
    {children}
  </div>
);

const ModulesPicker = ({ modules, value, onChange }) => (
  <Popover>
    <PopoverTrigger asChild>
      <button type="button" className="h-9 px-3 border rounded-md bg-white text-sm text-left flex items-center justify-between" data-testid="audit-filter-modules">
        <span className="truncate">{value.length ? `${value.length} seleccionado(s)` : 'Todos los módulos'}</span>
        <ChevronDown size={14} className="text-slate-400 shrink-0" />
      </button>
    </PopoverTrigger>
    <PopoverContent className="w-64 p-2" align="start">
      {modules.map((m) => (
        <label key={m} className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-slate-50 text-sm cursor-pointer">
          <Checkbox checked={value.includes(m)} data-testid={`audit-module-opt-${m}`}
            onCheckedChange={(c) => onChange(c ? [...value, m] : value.filter((x) => x !== m))} />
          {m}
        </label>
      ))}
    </PopoverContent>
  </Popover>
);

export const AuditFilters = ({ options, filters, setFilters, onSearch, onReset }) => {
  const set = (k) => (e) => setFilters({ ...filters, [k]: e?.target ? e.target.value : e });
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSearch(); }} className="bg-white border rounded-xl p-4 grid grid-cols-1 md:grid-cols-4 xl:grid-cols-8 gap-3 items-end" data-testid="audit-filters">
      <Field label="Desde"><Input type="datetime-local" value={filters.date_from} onChange={set('date_from')} data-testid="audit-filter-from" /></Field>
      <Field label="Hasta"><Input type="datetime-local" value={filters.date_to} onChange={set('date_to')} data-testid="audit-filter-to" /></Field>
      <Field label="Módulo"><ModulesPicker modules={options.modules || []} value={filters.modules} onChange={set('modules')} /></Field>
      <Field label="Acción">
        <Select value={filters.action} onValueChange={set('action')}>
          <SelectTrigger data-testid="audit-filter-action"><SelectValue /></SelectTrigger>
          <SelectContent>
            {['TODAS', 'CREATE', 'UPDATE', 'DELETE'].map((a) => <SelectItem key={a} value={a} data-testid={`audit-action-opt-${a}`}>{a}</SelectItem>)}
          </SelectContent>
        </Select>
      </Field>
      <Field label="Usuario">
        <Input list="audit-users-list" placeholder="Nombre o email" value={filters.user} onChange={set('user')} data-testid="audit-filter-user" />
        <datalist id="audit-users-list">
          {(options.users || []).map((u) => <option key={u.email} value={u.email}>{u.name}</option>)}
        </datalist>
      </Field>
      <Field label="ID / Correlativo"><Input placeholder="COT-2026-..." value={filters.registro} onChange={set('registro')} data-testid="audit-filter-registro" /></Field>
      <Field label="Campo modificado"><Input placeholder="ej. lockout_minutes" value={filters.field} onChange={set('field')} data-testid="audit-filter-field" /></Field>
      <div className="flex gap-2">
        <Button type="submit" className="flex-1 bg-[#003366] hover:bg-[#00254d]" data-testid="audit-search-btn"><Search size={14} className="mr-1" />Buscar</Button>
        <Button type="button" variant="outline" onClick={onReset} title="Limpiar filtros" data-testid="audit-reset-btn"><RotateCcw size={14} /></Button>
      </div>
    </form>
  );
};
