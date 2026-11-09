import { GitBranch } from 'lucide-react';
import { LevelTag } from './levels';

// contacts: contactos de niveles SUPERIORES (con scope/effective). ownHasContacts: si el nivel actual define los suyos.
export const InheritedContactsPanel = ({ contacts = [], ownHasContacts, testId = 'inherited-contacts-panel' }) => {
  if (!contacts.length) return null;
  return (
    <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg" data-testid={testId}>
      <div className="flex items-center gap-2 mb-1">
        <GitBranch size={14} className="text-indigo-600" />
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">Contactos heredados (solo lectura)</h4>
      </div>
      <p className="text-[11px] text-slate-500 mb-2">
        {ownHasContacts
          ? 'Este nivel define contactos propios: sustituyen a los heredados para él y sus niveles inferiores.'
          : 'Sin contactos propios: este nivel adopta los contactos marcados "En uso".'}
      </p>
      <div className="space-y-1">
        {contacts.map((c, i) => (
          <div key={`${c.scope}-${c.contact_id || i}`} className="flex items-center gap-2 text-xs text-slate-600 bg-white rounded px-2 py-1.5 border border-slate-100" data-testid={`inherited-contact-${i}`}>
            <LevelTag scope={c.scope} />
            <span className="font-medium text-slate-700">{c.full_name || '—'}</span>
            <span className="text-slate-400">·</span>
            <span className="truncate">{c.email}</span>
            {c.level_name && <span className="text-[10px] text-slate-400 truncate">({c.level_name})</span>}
            {c.effective && !ownHasContacts && <span className="ml-auto text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 rounded-full" data-testid={`inherited-contact-effective-${i}`}>En uso</span>}
          </div>
        ))}
      </div>
    </div>
  );
};
