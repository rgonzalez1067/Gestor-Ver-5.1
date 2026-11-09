import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Label } from '../../ui/label';
import { SlidersHorizontal } from 'lucide-react';
import { useClientCatalogs } from './useClientCatalogs';
import { LEVELS } from './levels';
import { SearchableSelect } from './SearchableSelect';

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
  const integratorNames = Array.from(new Set(cat.integrators.map(i => i.name).filter(Boolean)))
    .sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));
  const tipos = Array.isArray(value.tipo_servicio) ? value.tipo_servicio : [];
  const curIntgName = value.integrador_id ? value.integrador_name : iv.integrador_name;
  const appDocs = cat.integrators.filter(i => i.name === curIntgName && (i.app_name || '').trim());
  const apps = Array.from(new Set(appDocs.map(i => i.app_name)));
  const pickIntegrator = (o) => {
    if (!o) return set({ integrador_id: '', integrador_name: '', aplicativo: '' });
    const docs = cat.integrators.filter(i => i.name === o.name);
    set({ integrador_id: docs[0]?.integrator_id || '', integrador_name: o.name, aplicativo: docs.length === 1 ? (docs[0].app_name || '') : '' });
  };
  const pickApp = (v) => {
    if (v === NONE) return set({ aplicativo: '' });
    const doc = appDocs.find(i => i.app_name === v);
    set(value.integrador_id && doc ? { aplicativo: v, integrador_id: doc.integrator_id } : { aplicativo: v });
  };

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
        <div>
          <Label className="text-xs">Integrador</Label>
          <SearchableSelect testId={`${testPrefix}-integrador_id`} disabled={disabled}
            value={value.integrador_id ? value.integrador_name : ''} emptyLabel={hint('integrador_id', iv.integrador_name)}
            options={integratorNames.map(n => ({ id: n, name: n }))}
            onChange={pickIntegrator} />
        </div>
        <div>
          <Label className="text-xs">Aplicativo</Label>
          <Select value={value.aplicativo || NONE} disabled={disabled || !apps.length} onValueChange={pickApp}>
            <SelectTrigger className="h-9" data-testid={`${testPrefix}-aplicativo`}><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>{apps.length ? hint('aplicativo') : 'Seleccione integrador'}</SelectItem>
              {apps.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
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
