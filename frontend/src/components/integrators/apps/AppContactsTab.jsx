import { Phone, Mail, User } from 'lucide-react';

export const AppContactsTab = ({ app }) => {
  const contacts = (app.contacts || []).filter((c) => (c.name || '').trim());
  return (
    <div className="space-y-3" data-testid="app-contacts-tab">
      <div className="rounded-md border border-slate-200 p-3 bg-slate-50">
        <p className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">Contacto Principal / Responsable del Integrador</p>
        <p className="text-sm font-semibold text-slate-800" data-testid="app-principal-contact">{app.principal_contact_name || '—'}</p>
        <div className="flex gap-4 text-xs text-slate-500 mt-0.5">
          {app.principal_contact_phone && <span className="inline-flex items-center gap-1"><Phone size={11} />{app.principal_contact_phone}</span>}
          {app.principal_contact_email && <span className="inline-flex items-center gap-1"><Mail size={11} />{app.principal_contact_email}</span>}
        </div>
      </div>
      <p className="text-[11px] uppercase tracking-wide text-slate-400">Directorio de Técnicos del Aplicativo ({contacts.length})</p>
      {contacts.length === 0 ? <p className="text-xs text-slate-400">Sin técnicos registrados.</p> : (
        <div className="grid md:grid-cols-2 gap-2">
          {contacts.map((c, i) => (
            <div key={c.contact_id || i} className="rounded-md border border-slate-200 p-2.5 bg-white" data-testid={`app-contact-${i}`}>
              <p className="text-sm font-semibold text-slate-800 flex items-center gap-1.5"><User size={13} />{c.name}{c.role && <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-50 text-cyan-700 font-normal">{c.role}</span>}</p>
              <div className="flex flex-wrap gap-x-4 text-xs text-slate-500 mt-0.5">
                {c.phone && <span className="inline-flex items-center gap-1"><Phone size={11} />{c.phone}</span>}
                {c.email && <span className="inline-flex items-center gap-1"><Mail size={11} />{c.email}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
