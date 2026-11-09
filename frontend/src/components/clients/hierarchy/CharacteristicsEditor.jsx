import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Label } from '../../ui/label';
import { SlidersHorizontal } from 'lucide-react';
import { useClientCatalogs } from './useClientCatalogs';
import { LEVELS } from './levels';

const SEGMENTS = ['Pymes', 'Corporativo', 'Emprendedor', 'Mixto'];
const TIPOS = ['VPOS', 'MPOS', 'Payment Gateway', 'Link de Pago'];
const NONE = '__inherit__';

// value: dict con los valores propios. inherited: {values, sources} del nivel superior.
export const CharacteristicsEditor = ({ value = {}, onChange, inherited, disabled, testPrefix = 'char' }) => {
  const cat = useClientCatalogs();
  const iv = inherited?.values || {};
  const src = inherited?.sources || {};
  const set = (patch) => onChange({ ...value, ...patch });
  const hint = (key, display) => {
    if (!iv[key] || (Array.isArray(iv[key]) && !iv[key].length)) return 'Sin definir';
    const lv = LEVELS[src[key]?.level]?.label || 'nivel superior';
    return `Heredar: ${display || iv[key]} (${lv})`;
  };

  const pair = (key, nameKey, options, label, labelOf) => (
    <div>
      <Label className="text-xs">{label}</Label>
      <Select value={value[key] || NONE} disabled={disabled}
        onValueChange={(v) => {
          if (v === NONE) return set({ [key]: '', [nameKey]: '' });
          const o = options.find(x => x.id === v);
          set({ [key]: v, [nameKey]: o?.name || '' });
        }}>
        <SelectTrigger className="h-9" data-testid={`${testPrefix}-${key}`}><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE}>{hint(key, iv[nameKey])}</SelectItem>
          {options.map(o => <SelectItem key={o.id} value={o.id}>{labelOf ? labelOf(o) : o.name}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  );

  const single = (key, options, label) => (
    <div>
      <Label className="text-xs">{label}</Label>
      <Select value={value[key] || NONE} disabled={disabled} onValueChange={(v) => set({ [key]: v === NONE ? '' : v })}>
        <SelectTrigger className="h-9" data-testid={`${testPrefix}-${key}`}><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE}>{hint(key)}</SelectItem>
          {options.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  );

  const users = (arr) => arr.map(u => ({ id: u.user_id, name: u.full_name }));
  const tipos = Array.isArray(value.tipo_servicio) ? value.tipo_servicio : [];
  const intg = cat.integrators.find(i => i.integrator_id === (value.integrador_id || iv.integrador_id));
  const apps = intg?.app_name ? [intg.app_name] : [];

  return (
    <div data-testid={`${testPrefix}-editor`}>
      <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5 mb-1"><SlidersHorizontal size={15} /> Características Comerciales y de Implementación</h3>
      <p className="text-[11px] text-slate-400 mb-3">Lo que defina aquí se hereda a los niveles inferiores. Deje "Heredar" para adoptar el valor del nivel superior.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {single('segment', SEGMENTS, 'Segmento')}
        {single('categoria_comercial', cat.categories.map(c => c.name), 'Categoría Comercial')}
        {pair('ejecutivo_user_id', 'ejecutivo_propietario', users(cat.ejecutivos), 'Ejecutivo Propietario')}
        {pair('coordinator_user_id', 'coordinator_name', users(cat.coordinadores), 'Coordinador')}
        {pair('implementer_user_id', 'implementer_name', users(cat.implementadores), 'Implementador')}
        {pair('integrador_id', 'integrador_name', cat.integrators.map(i => ({ id: i.integrator_id, name: i.name })), 'Integrador')}
        {single('aplicativo', apps, 'Aplicativo')}
        {single('modelo_impresora_fiscal', cat.printers.map(p => p.name), 'Impresora Fiscal')}
        <div>
          <Label className="text-xs">Tipo de Servicio</Label>
          <div className="flex flex-wrap gap-1.5 mt-1" data-testid={`${testPrefix}-tipo_servicio`}>
            {TIPOS.map(t => {
              const on = tipos.includes(t);
              return (
                <button key={t} type="button" disabled={disabled} data-testid={`${testPrefix}-tipo-${t.replace(/\s+/g, '-')}`}
                  onClick={() => set({ tipo_servicio: on ? tipos.filter(x => x !== t) : [...tipos, t] })}
                  className={`px-2 py-1 rounded-full text-[11px] border transition-colors ${on ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400'}`}>
                  {t}
                </button>
              );
            })}
          </div>
          {!tipos.length && <p className="text-[10px] text-slate-400 mt-1">{hint('tipo_servicio', (iv.tipo_servicio || []).join(', '))}</p>}
        </div>
      </div>
    </div>
  );
};
