import { GitBranch, MapPin, Eye } from 'lucide-react';

const contactOf = (b) => {
  const c = b.contacts?.[0];
  if (c) return { name: c.full_name || `${c.first_name || ''} ${c.last_name || ''}`.trim(), extra: [c.role, c.phone].filter(Boolean).join(' · ') };
  if (b.contact1?.name) return { name: b.contact1.name, extra: b.contact1.email || '' };
  return null;
};

export const BranchesDrilldown = ({ parent, branches }) => (
  <div className="ml-6 my-1 border-l-2 border-amber-300 pl-4" data-testid={`branches-drilldown-${parent.client_id}`}>
    <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700 mb-1.5 flex items-center gap-1.5">
      <GitBranch size={12} /> {branches.length} sucursal(es) de {parent.legal_name}
      <span className="ml-2 inline-flex items-center gap-1 font-normal normal-case text-slate-400"><Eye size={11} />Solo consulta — gestiónelas desde «Gestionar Sucursales»</span>
    </p>
    <div className="bg-white border border-amber-100 rounded-md overflow-hidden">
      <table className="w-full text-xs">
        <thead className="!static bg-amber-50/60 text-[10px] uppercase text-slate-500">
          <tr>
            <th className="px-3 py-1.5 text-left">Sucursal</th><th className="px-3 py-1.5 text-left">Nombre Fantasía / Marca</th>
            <th className="px-3 py-1.5 text-left">Dirección</th><th className="px-3 py-1.5 text-left">Segmento</th>
            <th className="px-3 py-1.5 text-left">Categoría</th><th className="px-3 py-1.5 text-left">Contacto Principal</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {branches.map((b) => {
            const ct = contactOf(b);
            return (
              <tr key={b.client_id} data-testid={`drilldown-branch-${b.client_id}`}>
                <td className="px-3 py-1.5 font-medium text-amber-800 whitespace-nowrap">{b.sucursal || 'Sucursal'}</td>
                <td className="px-3 py-1.5 text-slate-700">{b.fantasy_name || b.marca_name || '—'}</td>
                <td className="px-3 py-1.5 text-slate-600 max-w-[260px]">
                  {b.branch_address || b.address ? <span className="inline-flex gap-1"><MapPin size={11} className="mt-0.5 shrink-0 text-slate-400" />{b.branch_address || b.address}</span> : '—'}
                </td>
                <td className="px-3 py-1.5 text-slate-600">{b.segment || '—'}</td>
                <td className="px-3 py-1.5 text-slate-600">{b.categoria_comercial || '—'}</td>
                <td className="px-3 py-1.5 text-slate-600">{ct ? <><span className="font-medium text-slate-700">{ct.name || '—'}</span>{ct.extra && <span className="block text-slate-400">{ct.extra}</span>}</> : '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
);
