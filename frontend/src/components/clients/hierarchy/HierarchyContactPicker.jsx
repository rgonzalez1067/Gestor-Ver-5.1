import { useState, useEffect } from 'react';
import { Checkbox } from '../../ui/checkbox';
import { Users } from 'lucide-react';
import api from '../../../utils/api';
import { LEVELS, LEVEL_ORDER, LevelTag } from './levels';

// Lista todos los contactos del árbol del cliente con su etiqueta de nivel.
// selected: emails seleccionados; onToggle(emails[], checked)
export const HierarchyContactPicker = ({ clientId, selected, onToggle }) => {
  const [contacts, setContacts] = useState([]);
  useEffect(() => {
    if (!clientId) return;
    api.get(`/clients/${clientId}/consolidated-contacts`)
      .then(r => setContacts((r.data?.contacts || []).filter(c => (c.email || '').includes('@'))))
      .catch(() => setContacts([]));
  }, [clientId]);
  if (!contacts.length) return null;
  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden max-h-56 overflow-y-auto" data-testid="hierarchy-contact-picker">
      <div className="px-3 py-1.5 bg-slate-50 text-[11px] font-semibold text-slate-600 flex items-center gap-1.5 border-b"><Users size={12} /> Contactos del árbol del cliente</div>
      {LEVEL_ORDER.map(scope => {
        const rows = contacts.filter(c => c.scope === scope);
        if (!rows.length) return null;
        const emails = rows.map(c => c.email);
        const allOn = emails.every(e => selected.includes(e));
        return (
          <div key={scope} data-testid={`picker-group-${scope}`}>
            <div className={`px-3 py-1 text-[10px] font-semibold uppercase border-y flex justify-between ${LEVELS[scope].tag}`}>
              <span>[{LEVELS[scope].label}] ({rows.length})</span>
              <button type="button" className="normal-case hover:underline" onClick={() => onToggle(emails, !allOn)} data-testid={`picker-group-toggle-${scope}`}>
                {allOn ? 'Deseleccionar bloque' : 'Seleccionar bloque'}
              </button>
            </div>
            {rows.map((c, i) => {
              const on = selected.includes(c.email);
              return (
                <label key={`${scope}-${c.contact_id || i}`} className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-blue-50/60 cursor-pointer" data-testid={`picker-contact-${scope}-${i}`}>
                  <Checkbox checked={on} onCheckedChange={(v) => onToggle([c.email], !!v)} data-testid={`picker-checkbox-${scope}-${i}`} />
                  <LevelTag scope={scope} />
                  <span className="font-medium text-slate-700">{c.full_name || '—'}</span>
                  <span className="text-slate-500 truncate">{c.email}</span>
                  {c.role && <span className="ml-auto text-[10px] text-slate-400">{c.role}</span>}
                </label>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
