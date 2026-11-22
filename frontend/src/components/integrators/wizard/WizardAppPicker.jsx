import { useMemo, useState } from 'react';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';

const NEW = '__new__';

// Aplicativo: elegir uno existente de la empresa o escribir uno nuevo.
export const WizardAppPicker = ({ apps, value, onChange }) => {
  const names = useMemo(() => Array.from(new Set(apps.map((a) => (a.app_name || '').trim()).filter(Boolean)))
    .sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' })), [apps]);
  const [custom, setCustom] = useState(() => !!value && !names.includes(value));
  const selected = custom ? NEW : (names.includes(value) ? value : '');

  return (
    <div className="space-y-2" data-testid="wizard-app-picker">
      <Label>Nombre del Aplicativo *</Label>
      <select className="h-10 w-full rounded-md border border-input bg-white px-3 text-sm" value={selected} data-testid="wizard-app-select"
        onChange={(e) => {
          const v = e.target.value;
          if (v === NEW) { setCustom(true); onChange(''); } else { setCustom(false); onChange(v); }
        }}>
        <option value="">Seleccione un aplicativo existente...</option>
        {names.map((n) => <option key={n} value={n}>{n}</option>)}
        <option value={NEW}>+ Otro aplicativo (nuevo)</option>
      </select>
      {custom && (
        <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder="Nombre del nuevo aplicativo" autoFocus data-testid="wizard-app-new-name" />
      )}
      {custom && value && names.some((n) => n.toLowerCase() === value.trim().toLowerCase()) && (
        <p className="text-[11px] text-amber-600" data-testid="wizard-app-duplicate-hint">Ese aplicativo ya existe: selecciónalo de la lista.</p>
      )}
    </div>
  );
};
