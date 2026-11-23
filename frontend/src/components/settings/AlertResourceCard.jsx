import { useMemo, useState } from 'react';
import { Switch } from '../ui/switch';
import { Input } from '../ui/input';
import { Users, Building, UserX, X, Search } from 'lucide-react';

const toggleIn = (list, v, off) => (off ? [...new Set([...list, v])] : list.filter((x) => x !== v));

const Section = ({ icon: Icon, title, hint, children }) => (
  <div className="border-t border-slate-100 pt-4">
    <p className="text-sm font-semibold text-slate-800 flex items-center gap-2"><Icon size={15} className="text-slate-500" />{title}</p>
    <p className="text-xs text-slate-500 mb-3">{hint}</p>
    {children}
  </div>
);

const UserPicker = ({ rid, users, disabled, onAdd }) => {
  const [q, setQ] = useState('');
  const matches = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return [];
    return users.filter((u) => !disabled.includes(u.user_id) && `${u.full_name} ${u.email}`.toLowerCase().includes(s)).slice(0, 8);
  }, [q, users, disabled]);
  return (
    <div className="relative max-w-md">
      <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
      <Input className="pl-8 h-9 text-sm" placeholder="Buscar persona para apagarle el aviso..." value={q} onChange={(e) => setQ(e.target.value)} data-testid={`ui-alerts-${rid}-user-search`} />
      {matches.length > 0 && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-slate-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
          {matches.map((u) => (
            <button key={u.user_id} type="button" className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50" onClick={() => { onAdd(u.user_id); setQ(''); }} data-testid={`ui-alerts-${rid}-user-option-${u.user_id}`}>
              <span className="font-medium text-slate-800">{u.full_name}</span>
              <span className="text-xs text-slate-500 ml-2">{u.departamento || 'Sin departamento'}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export const AlertResourceCard = ({ rid, title, description, rule, departments, users, onChange }) => {
  const byId = useMemo(() => Object.fromEntries(users.map((u) => [u.user_id, u])), [users]);
  const set = (patch) => onChange({ ...rule, ...patch });
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4" data-testid={`ui-alerts-card-${rid}`}>
      <div>
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
      <Section icon={Users} title="Todos los usuarios" hint="Interruptor general. Si está apagado, nadie ve este aviso.">
        <label className="flex items-center gap-3">
          <Switch checked={rule.enabled} onCheckedChange={(v) => set({ enabled: v })} data-testid={`ui-alerts-${rid}-global`} />
          <span className={`text-sm font-medium ${rule.enabled ? 'text-emerald-700' : 'text-slate-500'}`}>{rule.enabled ? 'Encendido' : 'Apagado para todos'}</span>
        </label>
      </Section>
      <Section icon={Building} title="Por departamento" hint="Apaga el aviso para todo un departamento.">
        <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 ${rule.enabled ? '' : 'opacity-50'}`}>
          {departments.map((d) => {
            const on = !rule.disabled_departments.includes(d);
            return (
              <label key={d} className="flex items-center justify-between gap-2 border border-slate-200 rounded-md px-3 py-2">
                <span className="text-sm text-slate-700 truncate">{d}</span>
                <Switch checked={on} onCheckedChange={(v) => set({ disabled_departments: toggleIn(rule.disabled_departments, d, !v) })} data-testid={`ui-alerts-${rid}-dept-${d}`} />
              </label>
            );
          })}
        </div>
      </Section>
      <Section icon={UserX} title="Por persona" hint="Personas a las que se les apaga el aviso, sin importar su departamento.">
        <UserPicker rid={rid} users={users} disabled={rule.disabled_users} onAdd={(id) => set({ disabled_users: toggleIn(rule.disabled_users, id, true) })} />
        <div className="flex flex-wrap gap-2 mt-3" data-testid={`ui-alerts-${rid}-users-off`}>
          {rule.disabled_users.length === 0 && <span className="text-xs text-slate-400 italic">Ninguna persona con el aviso apagado.</span>}
          {rule.disabled_users.map((id) => (
            <span key={id} className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              {byId[id]?.full_name || id}<span className="text-slate-400">· {byId[id]?.departamento || '—'}</span>
              <button type="button" onClick={() => set({ disabled_users: toggleIn(rule.disabled_users, id, false) })} className="text-slate-400 hover:text-red-600" data-testid={`ui-alerts-${rid}-user-remove-${id}`}><X size={12} /></button>
            </span>
          ))}
        </div>
      </Section>
    </div>
  );
};
